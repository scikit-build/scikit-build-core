"""
Shared CMake-build orchestration for the wheel backend (``build/wheel.py``) and
the hatchling plugin (``hatch/plugin.py``).

These helpers cover the band that is identical between the two callers: tag
computation, build/wheel/install directory layout, and running
configure/build/install. The wheel-assembly side (WheelWriter vs hatchling
``build_data`` delegation) deliberately stays in each caller.
"""

from __future__ import annotations

import dataclasses
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
from ._pathutil import resolve_wheel_tree

if TYPE_CHECKING:
    from collections.abc import Mapping

    from packaging.version import Version

    from ..cmake import CMake
    from ..settings.skbuild_model import ScikitBuildSettings

__all__ = ["WheelDirs", "configure_build_install", "prepare_wheel_dirs"]

WheelState = Literal[
    "sdist", "wheel", "editable", "metadata_wheel", "metadata_editable"
]


def __dir__() -> list[str]:
    return __all__


@dataclasses.dataclass
class WheelDirs:
    wheel_dirs: dict[str, Path]
    install_dir: Path
    build_dir: Path
    tags: WheelTag
    targetlib: str


def prepare_wheel_dirs(
    *,
    settings: ScikitBuildSettings,
    wheel_root: Path,
    build_tmp_folder: Path,
    state: WheelState,
    editable: bool,
    has_cmake: bool,
) -> WheelDirs:
    """
    Compute the wheel tag, build directory, the ``wheel_dirs`` layout, and the
    install directory. Creates the ``wheel_dirs`` directories.
    """
    if settings.wheel.platlib is None:
        targetlib = "platlib" if settings.wheel.cmake else "purelib"
    else:
        targetlib = "platlib" if settings.wheel.platlib else "purelib"

    cmake_args = get_cmake_args_from_settings(settings, os.environ)
    tags = WheelTag.compute_best(
        archs_to_tags(get_archs(os.environ, cmake_args)),
        settings.wheel.py_api,
        expand_macos=settings.wheel.expand_macos_universal_tags,
        root_is_purelib=targetlib == "purelib",
        build_tag=settings.wheel.build_tag,
        cmake_defines=settings.cmake.define,
        cmake_args=cmake_args,
    )

    if has_cmake and editable and settings.editable.mode == "inplace":
        build_dir = Path(settings.cmake.source_dir)
    else:
        build_dir = (
            Path(
                settings.build_dir.format(
                    **pyproject_format(settings=settings, tags=tags, state=state)
                )
            )
            if settings.build_dir
            else build_tmp_folder / "build"
        )
    logger.info("Build directory: {}", build_dir.resolve())

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

    install_base, install_rest = resolve_wheel_tree(
        settings.wheel.install_dir,
        wheel_dirs=wheel_dirs,
        targetlib=targetlib,
        experimental=settings.experimental,
    )
    install_dir = install_base / install_rest

    return WheelDirs(
        wheel_dirs=wheel_dirs,
        install_dir=install_dir,
        build_dir=build_dir,
        tags=tags,
        targetlib=targetlib,
    )


def configure_build_install(
    *,
    cmake: CMake,
    settings: ScikitBuildSettings,
    wheel_dirs: dict[str, Path],
    install_dir: Path,
    build_dir: Path,
    state: WheelState,
    name: str,
    version: Version,
    editable: bool,
    extra_cache_entries: Mapping[str, str | Path] | None = None,
    exit_after_config: bool = False,
) -> tuple[Builder, list[str], list[str]]:
    """
    Configure, build, and install the CMake project into ``wheel_dirs``.

    Returns the :class:`Builder` along with the ``build_options`` and
    ``install_options`` (``--config``/``-v``) derived from the resolved
    generator. The install step is skipped for editable inplace builds. When
    ``exit_after_config`` is set, returns right after configuring (with empty
    option lists) so callers can stop early.
    """
    config = CMaker(
        cmake,
        source_dir=settings.cmake.source_dir,
        build_dir=build_dir,
        build_type=settings.cmake.build_type,
    )
    builder = Builder(settings=settings, config=config)

    rich_print("{green}***", "{bold}Configuring CMake...")
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

    build_options: list[str] = []
    install_options: list[str] = []

    if exit_after_config:
        return builder, build_options, install_options

    default_gen = (
        "MSVC" if sysconfig.get_platform().startswith("win") else "Default Generator"
    )
    generator = builder.get_generator() or default_gen
    rich_print(
        "{green}***",
        f"{{bold}}Building project with {{blue}}{generator}{{default}}...",
    )
    builder.build(build_args=[])

    if not (editable and settings.editable.mode == "inplace"):
        rich_print("{green}***", "{bold}Installing project into wheel...")
        builder.install(install_dir)

    if not builder.config.single_config and builder.config.build_type:
        build_options += ["--config", builder.config.build_type]
        install_options += ["--config", builder.config.build_type]
    if builder.settings.cmake.verbose:
        build_options.append("-v")

    return builder, build_options, install_options
