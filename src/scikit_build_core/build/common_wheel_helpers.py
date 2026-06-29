"""
Shared CMake-build orchestration for the wheel backend (``build/wheel.py``) and
the hatchling plugin (``hatch/plugin.py``).

These helpers cover the band that is identical between the two callers: tag
computation, build/wheel/install directory layout, and running
configure/build/install. The wheel-assembly side (WheelWriter vs hatchling
``build_data`` delegation) deliberately stays in each caller.
"""

from __future__ import annotations

import os
import sysconfig
from pathlib import Path
from typing import TYPE_CHECKING, Literal

from .._logging import logger, rich_print
from ..builder.builder import (
    Builder,
    archs_to_tags,
    get_archs,
    get_cmake_args_from_settings,
)
from ..builder.wheel_tag import WheelTag
from ..cmake import CMaker
from ..format import pyproject_format
from ..settings.skbuild_model import normalize_build_types
from ._pathutil import resolve_wheel_tree

if TYPE_CHECKING:
    from collections.abc import Mapping

    from packaging.version import Version

    from ..cmake import CMake
    from ..settings.skbuild_model import ScikitBuildSettings

__all__ = [
    "build_install_extra_build_types",
    "build_wheel",
    "configure_wheel",
    "editable_rebuild_options",
    "get_build_dir",
    "get_editable_rebuild_dir",
    "get_install_dir",
    "get_targetlib",
    "get_wheel_tag",
    "install_wheel",
    "prepare_wheel_dirs",
]

WheelState = Literal[
    "sdist", "wheel", "editable", "metadata_wheel", "metadata_editable"
]
TargetLib = Literal["platlib", "purelib"]


def __dir__() -> list[str]:
    return __all__


def get_targetlib(settings: ScikitBuildSettings) -> TargetLib:
    """
    The wheel lib directory the build targets. ``wheel.platlib`` forces the
    choice; otherwise a CMake build is platlib and a Python-only build purelib.
    """
    if settings.wheel.platlib is None:
        return "platlib" if settings.wheel.cmake else "purelib"
    return "platlib" if settings.wheel.platlib else "purelib"


def get_wheel_tag(settings: ScikitBuildSettings, *, targetlib: TargetLib) -> WheelTag:
    """Compute the best wheel tag for the current environment."""
    cmake_args = get_cmake_args_from_settings(settings, os.environ)
    return WheelTag.compute_best(
        archs_to_tags(get_archs(os.environ, cmake_args)),
        settings.wheel.py_api,
        expand_macos=settings.wheel.expand_macos_universal_tags,
        root_is_purelib=targetlib == "purelib",
        build_tag=settings.wheel.build_tag,
        cmake_defines=settings.cmake.define,
        cmake_args=cmake_args,
    )


def get_build_dir(
    settings: ScikitBuildSettings,
    *,
    tags: WheelTag,
    state: WheelState,
    editable: bool,
    has_cmake: bool,
    fallback: Path,
) -> Path:
    """
    Where CMake configures and builds: the source dir for inplace editable
    builds, the (formatted) configured ``build-dir``, or ``fallback`` otherwise.
    """
    if has_cmake and editable and settings.editable.mode == "inplace":
        build_dir = Path(settings.cmake.source_dir)
    elif settings.build_dir:
        build_dir = Path(
            settings.build_dir.format(
                **pyproject_format(settings=settings, tags=tags, state=state)
            )
        )
    else:
        build_dir = fallback
    logger.info("Build directory: {}", build_dir.resolve())
    return build_dir


def get_editable_rebuild_dir(
    settings: ScikitBuildSettings,
    *,
    build_dir: Path,
    targetlib: TargetLib,
    tags: WheelTag,
    state: WheelState,
) -> Path:
    """
    Persistent install tree for a rebuildable redirect editable.

    ``editable.rebuild-dir`` (formatted like ``build-dir``) overrides the default
    ``install/<targetlib>`` tree inside ``build-dir``. The redirect references the
    compiled artifacts here by absolute path, so it must be stable between build
    and run time (#1135).
    """
    if settings.editable.rebuild_dir:
        return Path(
            settings.editable.rebuild_dir.format(
                **pyproject_format(settings=settings, tags=tags, state=state)
            )
        ).resolve()
    return (build_dir / "install" / targetlib).resolve()


def prepare_wheel_dirs(wheel_root: Path, *, targetlib: TargetLib) -> dict[str, Path]:
    """Create the staging wheel tree under ``wheel_root`` and return its dirs."""
    wheel_dirs = {
        targetlib: wheel_root / targetlib,
        "data": wheel_root / "data",
        "headers": wheel_root / "headers",
        "scripts": wheel_root / "scripts",
        "null": wheel_root / "null",
        "metadata": wheel_root / "metadata",
    }
    for d in wheel_dirs.values():
        d.mkdir(parents=True)
    return wheel_dirs


def get_install_dir(
    settings: ScikitBuildSettings,
    *,
    wheel_dirs: Mapping[str, Path],
    targetlib: TargetLib,
) -> Path:
    """Resolve ``wheel.install-dir`` to an absolute path inside the wheel tree."""
    base, rest = resolve_wheel_tree(
        settings.wheel.install_dir,
        wheel_dirs=wheel_dirs,
        targetlib=targetlib,
        experimental=settings.experimental,
    )
    return base / rest


def configure_wheel(
    *,
    cmake: CMake,
    settings: ScikitBuildSettings,
    wheel_dirs: Mapping[str, Path],
    install_dir: Path,
    build_dir: Path,
    state: WheelState,
    name: str,
    version: Version,
    extra_cache_entries: Mapping[str, str | Path] | None = None,
    build_type: str | None = None,
) -> Builder:
    """
    Configure the CMake project, returning the
    :class:`~scikit_build_core.builder.builder.Builder` to build with.

    Defaults to the primary (first) build type. It is rerunnable: pass an extra
    ``build_type`` to reconfigure a single-config generator into a fresh builder
    for that build type (see :func:`build_install_extra_build_types`).
    """
    if build_type is None:
        build_type = normalize_build_types(settings.cmake.build_type)[0]
        rich_print("{green}***", "{bold}Configuring CMake...")
    else:
        rich_print(
            "{green}***",
            f"{{bold}}Reconfiguring CMake for {{blue}}{build_type}{{default}}...",
        )

    config = CMaker(
        cmake,
        source_dir=settings.cmake.source_dir,
        build_dir=build_dir,
        build_type=build_type,
    )
    builder = Builder(settings=settings, config=config)

    # Setting the install prefix because some libs hardcode CMAKE_INSTALL_PREFIX
    # Otherwise `cmake --install --prefix` would work by itself
    defines = {"CMAKE_INSTALL_PREFIX": install_dir}
    cache_entries: dict[str, str | Path] = {
        f"SKBUILD_{k.upper()}_DIR": v for k, v in wheel_dirs.items()
    }
    cache_entries["SKBUILD_STATE"] = state
    if extra_cache_entries:
        cache_entries.update(extra_cache_entries)
    builder.configure(
        defines=defines,
        cache_entries=cache_entries,
        name=name,
        version=version,
    )
    return builder


def build_wheel(builder: Builder) -> None:
    """Build the configured CMake project."""
    default_gen = (
        "MSVC" if sysconfig.get_platform().startswith("win") else "Default Generator"
    )
    generator = builder.get_generator() or default_gen
    rich_print(
        "{green}***",
        f"{{bold}}Building project with {{blue}}{generator}{{default}}...",
    )
    builder.build(build_args=[])


def install_wheel(builder: Builder, *, install_dir: Path, editable: bool) -> None:
    """
    Install the built project into the wheel tree.

    Skipped for editable inplace builds, which load from the build tree directly.
    """
    if editable and builder.settings.editable.mode == "inplace":
        return
    rich_print("{green}***", "{bold}Installing project into wheel...")
    builder.install(install_dir)


def build_install_extra_build_types(
    builder: Builder,
    *,
    settings: ScikitBuildSettings,
    wheel_dirs: Mapping[str, Path],
    install_dir: Path,
    state: WheelState,
    name: str,
    version: Version,
    editable: bool,
    extra_cache_entries: Mapping[str, str | Path] | None = None,
) -> None:
    """
    Build and install build types beyond the primary into the same wheel.

    Single-config generators (Ninja, Makefiles) are reconfigured into a fresh
    builder for each extra build type; multi-config generators just build the
    extra ``--config`` with the original builder. Everything installs to the same
    prefix. Call this after the primary build and install.
    """
    build_types = normalize_build_types(settings.cmake.build_type)
    for extra_build_type in build_types[1:]:
        if builder.config.single_config:
            builder = configure_wheel(
                cmake=builder.config.cmake,
                build_dir=builder.config.build_dir,
                build_type=extra_build_type,
                settings=settings,
                wheel_dirs=wheel_dirs,
                install_dir=install_dir,
                state=state,
                name=name,
                version=version,
                extra_cache_entries=extra_cache_entries,
            )
        rich_print(
            "{green}***",
            f"{{bold}}Building {{blue}}{extra_build_type}{{default}} project...",
        )
        builder.build(build_args=[], build_type=extra_build_type)
        if not (editable and settings.editable.mode == "inplace"):
            rich_print(
                "{green}***",
                f"{{bold}}Installing {{blue}}{extra_build_type}{{default}} project into wheel...",
            )
            builder.install(install_dir, build_type=extra_build_type)

    # A single-config rebuild shim shares this build directory and runs
    # ``cmake --build`` without a ``--config`` (it was given the primary build
    # type's options), so the loop above must not leave it on the last extra
    # type. Restore the primary configuration so import-time rebuilds refresh it.
    if (
        len(build_types) > 1
        and builder.config.single_config
        and editable
        and settings.editable.mode == "redirect"
        and (settings.editable.rebuild or bool(settings.editable.rebuild_dir))
    ):
        configure_wheel(
            cmake=builder.config.cmake,
            build_dir=builder.config.build_dir,
            build_type=build_types[0],
            settings=settings,
            wheel_dirs=wheel_dirs,
            install_dir=install_dir,
            state=state,
            name=name,
            version=version,
            extra_cache_entries=extra_cache_entries,
        )


def editable_rebuild_options(builder: Builder) -> tuple[list[str], list[str]]:
    """
    Flags so an editable rebuild reproduces this build's config selection.

    Returns ``(build_options, install_options)`` for the redirect shim's runtime
    ``cmake --build`` / ``cmake --install``. Deliberately a subset: it excludes
    ``--prefix`` (the shim supplies its own), ``--strip``, and components.
    """
    build_options: list[str] = []
    install_options: list[str] = []
    if not builder.config.single_config and builder.config.build_type:
        build_options += ["--config", builder.config.build_type]
        install_options += ["--config", builder.config.build_type]
    if builder.settings.cmake.verbose:
        build_options.append("-v")
    return build_options, install_options
