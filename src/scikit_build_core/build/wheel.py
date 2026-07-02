from __future__ import annotations

__lazy_modules__ = {
    f"{(__spec__.parent or '').rsplit('.', 1)[0]}._compat",
    f"{(__spec__.parent or '').rsplit('.', 1)[0]}._compat.typing",
    f"{(__spec__.parent or '').rsplit('.', 1)[0]}._logging",
    f"{(__spec__.parent or '').rsplit('.', 1)[0]}._variants",
    f"{(__spec__.parent or '').rsplit('.', 1)[0]}.cmake",
    f"{(__spec__.parent or '').rsplit('.', 1)[0]}.errors",
    f"{(__spec__.parent or '').rsplit('.', 1)[0]}.settings.skbuild_read_settings",
    f"{__spec__.parent}._editable",
    f"{__spec__.parent}._init",
    f"{__spec__.parent}._pathutil",
    f"{__spec__.parent}._scripts",
    f"{__spec__.parent}._wheelfile",
    f"{__spec__.parent}.common_wheel_helpers",
    f"{__spec__.parent}.generate",
    f"{__spec__.parent}.metadata",
    "functools",
    "packaging",
    "packaging.requirements",
    "packaging.tags",
    "packaging.utils",
    "pathlib",
    "pathspec",
    "platform",
    "shutil",
    "tempfile",
    "typing",
}

import dataclasses
import functools
import os
import platform
import shutil
import sys
import tempfile
from pathlib import Path
from typing import Any, Literal

import pathspec
from packaging.requirements import Requirement
from packaging.tags import Tag
from packaging.utils import canonicalize_name

from .._compat import tomllib
from .._compat.typing import assert_never
from .._logging import LEVEL_VALUE, logger, rich_error, rich_print
from .._variants import get_wheel_variant
from ..cmake import CMake
from ..errors import FailedLiveProcessError
from ..settings.skbuild_read_settings import SettingsReader
from ._editable import (
    editable_inplace_files,
    editable_redirect_files,
    get_packages,
    package_search_dirs,
)
from ._init import setup_logging
from ._pathutil import (
    NON_PLATLIB_REBUILD_MSG,
    editable_redirectable,
    iter_force_include,
    packages_to_file_mapping,
    resolve_from_sdist_force_include,
    resolve_wheel_tree,
)
from ._scripts import process_script_dir
from ._wheelfile import WheelMetadata, WheelWriter
from .common_wheel_helpers import (
    build_install_extra_build_types,
    build_wheel,
    configure_wheel,
    editable_rebuild_options,
    get_build_dir,
    get_editable_rebuild_dir,
    get_install_dir,
    get_targetlib,
    get_wheel_tag,
    install_wheel,
    prepare_editable_rebuild_dir,
    prepare_wheel_dirs,
)
from .generate import generate_file_contents
from .metadata import get_standard_metadata

TYPE_CHECKING = False
if TYPE_CHECKING:
    from collections.abc import Iterable, Sequence

    from ..settings.skbuild_model import ScikitBuildSettings

__all__ = ["_build_wheel_impl"]


def __dir__() -> list[str]:
    return __all__


def _make_editable(
    *,
    build_options: Sequence[str] = (),
    install_options: Sequence[str] = (),
    libdir: Path,
    mapping: dict[str, str],
    name: str,
    reload_dir: Path | None,
    settings: ScikitBuildSettings,
    wheel: WheelWriter,
    packages: Iterable[str],
    install_prefix: str | None = None,
) -> None:
    for filename, contents in editable_redirect_files(
        build_options=build_options,
        install_options=install_options,
        libdir=libdir,
        mapping=mapping,
        name=name,
        packages=packages,
        reload_dir=reload_dir,
        settings=settings,
        install_prefix=install_prefix,
    ).items():
        wheel.writestr(filename, contents)


def _force_include_into_wheel(
    settings: ScikitBuildSettings,
    *,
    wheel_dirs: dict[str, Path],
    targetlib: str,
    only_metadata: bool = False,
    redirect_mapping: dict[str, str] | None = None,
    redirect_libdir: Path | None = None,
) -> set[Path]:
    """
    Copy ``wheel.force-include`` entries into the staged wheel trees.

    Run after the package copy and CMake install so force-included files override
    files at the same destination. ``only_metadata`` restricts the copy to the
    metadata tree; the prepare-metadata path uses it so the prepared
    ``.dist-info`` matches the final wheel.

    With ``redirect_mapping``/``redirect_libdir`` (a redirect-mode editable
    build), platlib entries the redirect can serve live (see
    :func:`editable_redirectable`) are added to the mapping instead of copied,
    displacing a package file or CMake output at the same destination so the
    force-include still wins. Everything else falls back to a baked copy.

    Returns the resolved target paths of force-included *files*, so the caller
    can exempt them from ``wheel.exclude`` (naming an exact file forces it past
    an exclude pattern). Files copied from a force-included *directory* are not
    returned, so a bulk directory copy stays subject to ``wheel.exclude``.
    """
    written: set[Path] = set()
    exclude_spec = (
        pathspec.GitIgnoreSpec.from_lines(settings.wheel.exclude)
        if redirect_mapping is not None
        else None
    )
    for source, dest in settings.wheel.force_include.items():
        base, rest = resolve_wheel_tree(
            dest,
            wheel_dirs=wheel_dirs,
            targetlib=targetlib,
            experimental=settings.experimental,
        )
        if only_metadata and base != wheel_dirs["metadata"]:
            continue
        # A source that names an sdist output exists only in an unpacked-sdist
        # build; from a source tree or editable build, fall back through the
        # sdist.force-include map to the original source.
        resolved = resolve_from_sdist_force_include(
            source, settings.sdist.force_include
        )
        source_is_file = Path(resolved).expanduser().is_file()
        for src_file, target in iter_force_include(resolved, rest, base):
            if redirect_mapping is not None and base == wheel_dirs[targetlib]:
                assert exclude_spec is not None
                assert redirect_libdir is not None
                rel = target.relative_to(base)
                # Directory members stay subject to wheel.exclude; with no
                # baked copy the zip-time filter never sees them, so filter
                # here. (A file force-include overrides the exclude.)
                if not source_is_file and exclude_spec.match_file(rel):
                    continue
                if editable_redirectable(src_file, rel):
                    live_target = str(redirect_libdir / rel)
                    # The force-include wins at its destination: drop a package
                    # mapping entry and staged/installed file at the same spot,
                    # since the finder checks installed files before sources.
                    for key in [
                        k for k, v in redirect_mapping.items() if v == live_target
                    ]:
                        del redirect_mapping[key]
                    target.unlink(missing_ok=True)
                    (redirect_libdir / rel).unlink(missing_ok=True)
                    redirect_mapping[str(src_file)] = live_target
                    continue
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src_file, target)
            if source_is_file:
                written.add(target.resolve())
    return written


@dataclasses.dataclass
class WheelImplReturn:
    wheel_filename: str
    settings: ScikitBuildSettings
    mapping: dict[str, str] = dataclasses.field(default_factory=dict)


def _build_wheel_impl(
    wheel_directory: str | None,
    config_settings: dict[str, list[str] | str] | None,
    metadata_directory: str | None,
    *,
    exit_after_config: bool = False,
    editable: bool,
) -> WheelImplReturn:
    """
    Build a wheel or just prepare metadata (if wheel dir is None). Can be editable.
    Handles one retry attempt if "failed" override present.
    """
    state: Literal["sdist", "wheel", "editable", "metadata_wheel", "metadata_editable"]
    if exit_after_config:
        state = "sdist"
    elif wheel_directory is None:
        state = "metadata_editable" if editable else "metadata_wheel"
    else:
        state = "editable" if editable else "wheel"

    pyproject_path = Path("pyproject.toml")
    with pyproject_path.open("rb") as ft:
        pyproject = tomllib.load(ft)

    settings_reader = SettingsReader(
        pyproject, config_settings or {}, state=state, retry=False
    )
    setup_logging(settings_reader.settings.logging.level)

    settings_reader.validate_may_exit()

    if settings_reader.settings.fail:
        if settings_reader.settings.messages.after_failure:
            rich_print(settings_reader.settings.messages.after_failure)
            raise SystemExit(7)
        rich_error("scikit-build-core's fail setting was enabled. Exiting immediately.")

    # Warn if cmake or ninja is in build-system.requires
    requirements = [
        canonicalize_name(Requirement(p).name)
        for p in pyproject.get("build-system", {}).get("requires", [])
    ]
    if "cmake" in requirements:
        logger.warning(
            "cmake should not be in build-system.requires - scikit-build-core will inject it as needed"
        )
    if "ninja" in requirements:
        logger.warning(
            "ninja should not be in build-system.requires - scikit-build-core will inject it as needed"
        )

    try:
        return _build_wheel_impl_impl(
            wheel_directory,
            metadata_directory,
            exit_after_config=exit_after_config,
            editable=editable,
            state=state,
            settings=settings_reader.settings,
            pyproject=pyproject,
        )
    except FailedLiveProcessError as err:
        settings_reader = SettingsReader(
            pyproject, config_settings or {}, state=state, retry=True
        )
        if "failed" not in settings_reader.overrides:
            err.msg = settings_reader.settings.messages.after_failure
            raise

        rich_print(
            "\n***",
            *err.args,
            "- retrying due to override...",
            color="yellow",
        )

        logger.setLevel(LEVEL_VALUE[settings_reader.settings.logging.level])

        settings_reader.validate_may_exit()

        try:
            return _build_wheel_impl_impl(
                wheel_directory,
                metadata_directory,
                exit_after_config=exit_after_config,
                editable=editable,
                state=state,
                settings=settings_reader.settings,
                pyproject=pyproject,
            )
        except FailedLiveProcessError as err2:
            err2.msg = settings_reader.settings.messages.after_failure
            raise


def _build_wheel_impl_impl(
    wheel_directory: str | None,
    metadata_directory: str | None,
    *,
    exit_after_config: bool = False,
    editable: bool,
    state: Literal["sdist", "wheel", "editable", "metadata_wheel", "metadata_editable"],
    settings: ScikitBuildSettings,
    pyproject: dict[str, Any],
) -> WheelImplReturn:
    """
    Build a wheel or just prepare metadata (if wheel dir is None). Can be editable.
    """

    metadata = get_standard_metadata(pyproject, settings, build_state=state)

    if metadata.version is None:
        msg = "project.version is not specified, must be statically present or tool.scikit-build metadata.version.provider configured when dynamic"
        raise AssertionError(msg)

    # Verify PEP 639 replaces license-files
    if metadata.license_files is not None and settings.wheel.license_files:
        msg = "Both project.license-files and tool.scikit-build.wheel.license-files are set, use only one"
        raise AssertionError(msg)

    # Get the closest (normally) importable name
    normalized_name = metadata.name.replace("-", "_").replace(".", "_")
    # Normalized like the wheel/sdist filename, for the {name} build-dir placeholder
    placeholder_name = metadata.canonical_name.replace("-", "_")

    if settings.wheel.cmake:
        cmake = CMake.default_search(version=settings.cmake.version, env=os.environ)
        cmake_msg = [f"using {{blue}}CMake {cmake.version}{{default}}"]
    else:
        cmake = None
        cmake_msg = []

    rich_print(
        "{green}*** {bold}scikit-build-core {__version__}",
        *cmake_msg,
        f"{{red}}({state})",
    )
    logger.info(
        "Implementation: {} {} on {}",
        sys.implementation.name,
        sys.platform,
        platform.machine(),
    )

    override_wheel_tags = None
    if settings.wheel.tags:
        override_wheel_tags = {Tag(*tag.split("-")) for tag in settings.wheel.tags}

    with tempfile.TemporaryDirectory() as tmpdir:
        build_tmp_folder = Path(tmpdir)
        wheel_dir = build_tmp_folder / "wheel"
        wheel_variant = get_wheel_variant(settings, pyproject, metadata)

        targetlib = get_targetlib(settings)
        tags = get_wheel_tag(settings, targetlib=targetlib)
        build_dir = get_build_dir(
            settings,
            tags=tags,
            state=state,
            editable=editable,
            has_cmake=cmake is not None,
            fallback=build_tmp_folder / "build",
            name=placeholder_name,
        )
        wheel_dirs = prepare_wheel_dirs(wheel_dir, targetlib=targetlib)
        install_dir = get_install_dir(
            settings, wheel_dirs=wheel_dirs, targetlib=targetlib
        )

        # A rebuildable redirect editable (one with a persistent build-dir)
        # installs the platlib into a persistent tree instead of the temporary
        # wheel-staging dir, and the redirect references the compiled artifacts
        # there by absolute path. This bakes SKBUILD_<targetlib>_DIR /
        # CMAKE_INSTALL_PREFIX at the final location at configure time, so
        # import-triggered rebuilds need no reconfigure (#1135).
        #
        # Two triggers: the classic editable.rebuild installs into a tree inside
        # build-dir; setting editable.rebuild-dir installs into a user-chosen tree
        # (see EditableSettings.rebuild_enabled). Both still require build-dir.
        editable_rebuild = (
            editable
            and settings.editable.mode == "redirect"
            and settings.editable.rebuild_enabled
            and bool(settings.build_dir)
        )
        if editable_rebuild:
            targetlib_dir = get_editable_rebuild_dir(
                settings,
                build_dir=build_dir,
                targetlib=targetlib,
                tags=tags,
                state=state,
                name=placeholder_name,
            )
            prepare_editable_rebuild_dir(
                targetlib_dir, guard=bool(settings.editable.rebuild_dir)
            )
        else:
            targetlib_dir = wheel_dirs[targetlib]

        # The metadata-only and full-wheel paths build identical WheelWriters
        # except for the output folder; share a single constructor.
        make_wheel = functools.partial(
            WheelWriter,
            metadata,
            tags=override_wheel_tags or tags.as_tags_set(),
            wheel_metadata=WheelMetadata(
                root_is_purelib=targetlib == "purelib",
                build_tag=settings.wheel.build_tag,
            ),
            metadata_dir=wheel_dirs["metadata"],
            variant_label=wheel_variant.label if wheel_variant else "",
            variant_dist_info_contents=(
                wheel_variant.dist_info_contents if wheel_variant else None
            ),
            reproducible=settings.wheel.reproducible,
        )

        # A rebuildable editable re-points install_dir into the persistent
        # install tree and bakes the same SKBUILD_<targetlib>_DIR so an absolute
        # ${SKBUILD_*_DIR}/... destination lands there too. The install tree only
        # covers the target lib, so wheel.install-dir must resolve under it; a
        # non-platlib (or absolute) tree cannot be rebuilt and raises the clear
        # guard here rather than a raw relative_to() ValueError.
        editable_rebuild_cache: dict[str, str | Path] | None = None
        if editable_rebuild:
            try:
                install_relative = install_dir.relative_to(wheel_dirs[targetlib])
            except ValueError:
                raise AssertionError(NON_PLATLIB_REBUILD_MSG) from None
            install_dir = targetlib_dir / install_relative
            editable_rebuild_cache = {f"SKBUILD_{targetlib.upper()}_DIR": targetlib_dir}

        # Include the metadata license.file entry if provided
        if metadata.license_files is not None:
            license_paths = metadata.license_files
        else:
            if settings.wheel.license_files is None:
                license_file_globs = [
                    "LICEN[CS]E*",
                    "COPYING*",
                    "NOTICE*",
                    "AUTHORS*",
                ]
            else:
                license_file_globs = list(settings.wheel.license_files)
            if (
                metadata.license
                and not isinstance(metadata.license, str)
                and metadata.license.file
            ):
                license_file_globs.append(str(metadata.license.file))

            license_paths = [
                x for y in license_file_globs for x in Path().glob(y) if x.is_file()
            ]

        for x in license_paths:
            path = wheel_dirs["metadata"] / "licenses" / x
            path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(x, path)

        if (
            settings.wheel.license_files
            and not (wheel_dirs["metadata"] / "licenses").is_dir()
        ):
            logger.warning(
                "No license files found, set wheel.license-files to [] to suppress this warning"
            )

        for gen in settings.generate:
            if gen.location == "source":
                contents = generate_file_contents(gen, metadata)
                gen.path.write_text(contents, encoding="utf-8")
                settings.sdist.include.append(gen.path.as_posix())

        if wheel_directory is None and not exit_after_config:
            if metadata_directory is None:
                msg = "metadata_directory must be specified if wheel_directory is None"
                raise AssertionError(msg)
            # Metadata-tree force-includes must land here too, so the prepared
            # .dist-info matches the final wheel (it is compared on build).
            _force_include_into_wheel(
                settings,
                wheel_dirs=wheel_dirs,
                targetlib=targetlib,
                only_metadata=True,
            )
            wheel = make_wheel(folder=Path(metadata_directory))
            dist_info_contents = wheel.dist_info_contents()
            dist_info = Path(metadata_directory) / f"{wheel.name_ver}.dist-info"
            dist_info.mkdir(parents=True)
            for key, data in dist_info_contents.items():
                path = dist_info / key
                if not path.parent.is_dir():
                    path.parent.mkdir(exist_ok=True, parents=True)
                path.write_bytes(data)
            return WheelImplReturn(wheel_filename=dist_info.name, settings=settings)

        for gen in settings.generate:
            contents = generate_file_contents(gen, metadata)
            if gen.location == "source":
                continue
            if gen.location == "build":
                path = build_dir / gen.path
            elif gen.location == "install":
                path = targetlib_dir / gen.path
            else:
                assert_never(gen.location)
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(contents, encoding="utf-8")

        build_options: list[str] = []
        install_options: list[str] = []

        if cmake is not None:
            builder = configure_wheel(
                cmake=cmake,
                settings=settings,
                wheel_dirs=wheel_dirs,
                install_dir=install_dir,
                build_dir=build_dir,
                state=state,
                extra_cache_entries=editable_rebuild_cache,
                name=metadata.name,
                version=metadata.version,
            )
            if exit_after_config:
                return WheelImplReturn("", settings=settings)
            build_wheel(builder)
            install_wheel(builder, install_dir=install_dir, editable=editable)
            build_options, install_options = editable_rebuild_options(builder)
            build_install_extra_build_types(
                builder,
                settings=settings,
                wheel_dirs=wheel_dirs,
                install_dir=install_dir,
                state=state,
                name=metadata.name,
                version=metadata.version,
                editable=editable,
                extra_cache_entries=editable_rebuild_cache,
            )

        assert wheel_directory is not None

        rich_print("{green}***", f"{{bold}}Making {state}...")
        packages = get_packages(
            packages=settings.wheel.packages,
            name=metadata.name,
        )
        assert settings.sdist.inclusion_mode is not None
        mapping = packages_to_file_mapping(
            packages=packages,
            platlib_dir=targetlib_dir,
            include=settings.sdist.include,
            src_exclude=settings.sdist.exclude,
            target_exclude=settings.wheel.exclude,
            build_dir=settings.build_dir,
            mode=settings.sdist.inclusion_mode,
        )

        if not editable:
            for filepath, package_dir in mapping.items():
                Path(package_dir).parent.mkdir(exist_ok=True, parents=True)
                shutil.copy2(filepath, package_dir)

        # Force-include into the wheel, after the package copy so entries
        # override package files and CMake output at the same destination. In a
        # redirect-mode editable, platlib entries the redirect can serve live
        # join the mapping instead of being baked in as stale copies.
        redirecting = editable and settings.editable.mode == "redirect"
        force_included = _force_include_into_wheel(
            settings,
            wheel_dirs=wheel_dirs,
            targetlib=targetlib,
            redirect_mapping=mapping if redirecting else None,
            redirect_libdir=targetlib_dir if redirecting else None,
        )

        # Normalize script shebangs after force-includes, so force-included
        # scripts (e.g. wheel = "/scripts/...") are processed too. Editable
        # installs still ship scripts (CMake-installed or force-included), so
        # normalize them as well.
        process_script_dir(wheel_dirs["scripts"])

        with make_wheel(folder=Path(wheel_directory)) as wheel:
            wheel.build(
                wheel_dirs,
                exclude=settings.wheel.exclude,
                exclude_exempt=force_included,
            )

            str_pkgs = package_search_dirs(packages)
            if editable and settings.editable.mode == "redirect":
                reload_dir = build_dir.resolve() if settings.build_dir else None

                _make_editable(
                    build_options=build_options,
                    install_options=install_options,
                    libdir=targetlib_dir,
                    mapping=mapping,
                    reload_dir=reload_dir,
                    settings=settings,
                    wheel=wheel,
                    name=normalized_name,
                    packages=str_pkgs,
                    install_prefix=os.fspath(install_dir) if editable_rebuild else None,
                )
            elif editable and settings.editable.mode == "inplace":
                if not packages:
                    msg = "Editable inplace mode requires at least one package"
                    raise AssertionError(msg)

                # Only an inplace CMake build has a persistent build dir to
                # rebuild in (get_build_dir returns the source dir). Without
                # CMake, build_dir is a temp dir that is deleted after the build,
                # so bake None and let rebuild() raise the friendly error instead
                # of recreating an empty temp dir and failing in CMake.
                for filename, editable_contents in editable_inplace_files(
                    name=normalized_name,
                    packages=packages,
                    package_paths=list(str_pkgs),
                    source_dir=build_dir.resolve() if cmake is not None else None,
                    build_options=build_options,
                    settings=settings,
                ).items():
                    wheel.writestr(filename, editable_contents)

    if metadata_directory is not None:
        dist_info_contents = wheel.dist_info_contents()
        dist_info = Path(metadata_directory)
        for key, data in dist_info_contents.items():
            path = dist_info / key
            previous_data = path.read_bytes()
            if previous_data != data:
                msg = f"Metadata mismatch in {key}"
                logger.error("{}: {!r} != {!r}", msg, previous_data, data)
                raise AssertionError(msg)

    wheel_filename: str = wheel.wheelpath.name
    rich_print("{green}***", f"{{bold}}Created{{normal}} {wheel_filename}")
    if settings.messages.after_success:
        rich_print(settings.messages.after_success)
    return WheelImplReturn(
        wheel_filename=wheel_filename, mapping=mapping, settings=settings
    )
