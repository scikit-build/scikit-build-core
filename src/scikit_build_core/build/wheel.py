from __future__ import annotations

import dataclasses
import os
import platform
import shutil
import sys
import sysconfig
import tempfile
from collections.abc import Mapping
from pathlib import Path
from typing import TYPE_CHECKING, Any, Literal

from packaging.requirements import Requirement
from packaging.utils import canonicalize_name

from .._compat import tomllib
from .._compat.typing import assert_never
from .._logging import LEVEL_VALUE, logger, rich_error, rich_print
from ..builder.builder import Builder, archs_to_tags, get_archs
from ..builder.wheel_tag import WheelTag
from ..cmake import CMake, CMaker
from ..errors import FailedLiveProcessError
from ..format import pyproject_format
from ..settings.skbuild_read_settings import SettingsReader
from ._editable import editable_redirect, libdir_to_installed, mapping_to_modules
from ._init import setup_logging
from ._pathutil import (
    packages_to_file_mapping,
)
from ._scripts import process_script_dir
from ._wheelfile import WheelMetadata, WheelWriter
from .generate import generate_file_contents
from .metadata import get_standard_metadata

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
) -> None:
    modules = mapping_to_modules(mapping, libdir)
    installed = libdir_to_installed(libdir)
    if settings.wheel.install_dir.startswith("/"):
        msg = "Editable installs cannot rebuild an absolute wheel.install-dir. Use an override to change if needed."
        raise AssertionError(msg)
    editable_txt = editable_redirect(
        modules=modules,
        installed=installed,
        reload_dir=reload_dir,
        rebuild=settings.editable.rebuild,
        verbose=settings.editable.verbose,
        build_options=build_options,
        install_options=install_options,
        install_dir=settings.wheel.install_dir,
    )

    wheel.writestr(
        f"_{name}_editable.py",
        editable_txt.encode(),
    )
    # Support Cython by adding the source directory directly to the path.
    # This is necessary because Cython does not support sys.meta_path for
    # cimports (as of 3.0.5).
    import_strings = [f"import _{name}_editable", *packages, ""]
    pth_import_paths = "\n".join(import_strings)
    wheel.writestr(
        f"_{name}_editable.pth",
        pth_import_paths.encode(),
    )


def _get_packages(
    *,
    packages: Sequence[str] | Mapping[str, str] | None,
    name: str,
) -> dict[str, str]:
    if packages is not None:
        if isinstance(packages, Mapping):
            return dict(packages)
        return {str(Path(p).name): p for p in packages}

    # Auto package discovery
    packages = {}
    for base_path in (Path("src"), Path("python"), Path()):
        path = base_path / name
        if path.is_dir() and (
            (path / "__init__.py").is_file() or (path / "__init__.pyi").is_file()
        ):
            logger.info("Discovered Python package at {}", path)
            packages[name] = str(path)
            break
    else:
        logger.debug("Didn't find a Python package for {}", name)

    return packages


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
            err2.msg = settings_reader.settings.messages.after_failure.format()
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

    metadata = get_standard_metadata(pyproject, settings)

    if metadata.version is None:
        msg = "project.version is not specified, must be statically present or tool.scikit-build metadata.version.provider configured when dynamic"
        raise AssertionError(msg)

    # Verify PEP 639 replaces license-files
    if metadata.license_files is not None and settings.wheel.license_files:
        msg = "Both project.license-files and tool.scikit-build.wheel.license-files are set, use only one"
        raise AssertionError(msg)

    # Get the closest (normally) importable name
    normalized_name = metadata.name.replace("-", "_").replace(".", "_")

    if settings.wheel.cmake:
        cmake = CMake.default_search(version=settings.cmake.version, env=os.environ)
        cmake_msg = [f"using {{blue}}CMake {cmake.version}{{default}}"]
    else:
        cmake = None
        cmake_msg = []

    if settings.wheel.platlib is None:
        targetlib = "platlib" if settings.wheel.cmake else "purelib"
    else:
        targetlib = "platlib" if settings.wheel.platlib else "purelib"

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

    with tempfile.TemporaryDirectory() as tmpdir:
        build_tmp_folder = Path(tmpdir)
        wheel_dir = build_tmp_folder / "wheel"

        tags = WheelTag.compute_best(
            archs_to_tags(get_archs(os.environ)),
            settings.wheel.py_api,
            expand_macos=settings.wheel.expand_macos_universal_tags,
            root_is_purelib=targetlib == "purelib",
            build_tag=settings.wheel.build_tag,
        )

        # A build dir can be specified, otherwise use a temporary directory
        if cmake is not None and editable and settings.editable.mode == "inplace":
            build_dir = settings.cmake.source_dir
        else:
            build_dir = (
                Path(
                    settings.build_dir.format(
                        **pyproject_format(
                            settings=settings,
                            tags=tags,
                            state=state,
                        )
                    )
                )
                if settings.build_dir
                else build_tmp_folder / "build"
            )
            logger.info("Build directory: {}", build_dir.resolve())

        wheel_dirs = {
            targetlib: wheel_dir / targetlib,
            "data": wheel_dir / "data",
            "headers": wheel_dir / "headers",
            "scripts": wheel_dir / "scripts",
            "null": wheel_dir / "null",
            "metadata": wheel_dir / "metadata",
        }

        for d in wheel_dirs.values():
            d.mkdir(parents=True)

        if ".." in settings.wheel.install_dir:
            msg = "wheel.install_dir must not contain '..'"
            raise AssertionError(msg)
        if settings.wheel.install_dir.startswith("/"):
            if not settings.experimental:
                msg = "Experimental features must be enabled to use absolute paths in wheel.install_dir"
                raise AssertionError(msg)
            if settings.wheel.install_dir[1:].split("/")[0] not in wheel_dirs:
                msg = "Must target a valid wheel directory"
                raise AssertionError(msg)
            install_dir = wheel_dir / settings.wheel.install_dir[1:]
        else:
            install_dir = wheel_dirs[targetlib] / settings.wheel.install_dir

        # Include the metadata license.file entry if provided
        if metadata.license_files:
            license_paths = metadata.license_files
        else:
            license_file_globs = settings.wheel.license_files or [
                "LICEN[CS]E*",
                "COPYING*",
                "NOTICE*",
                "AUTHORS*",
            ]
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
            shutil.copy(x, path)

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
                gen.path.write_text(contents)
                settings.sdist.include.append(str(gen.path))

        if wheel_directory is None and not exit_after_config:
            if metadata_directory is None:
                msg = "metadata_directory must be specified if wheel_directory is None"
                raise AssertionError(msg)
            wheel = WheelWriter(
                metadata,
                Path(metadata_directory),
                tags.as_tags_set(),
                WheelMetadata(
                    root_is_purelib=targetlib == "purelib",
                    build_tag=settings.wheel.build_tag,
                ),
                wheel_dirs["metadata"],
            )
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
                path = wheel_dirs[targetlib] / gen.path
            else:
                assert_never(gen.location)
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(contents, encoding="utf-8")

        build_options = []
        install_options = []

        if cmake is not None:
            config = CMaker(
                cmake,
                source_dir=settings.cmake.source_dir,
                build_dir=build_dir,
                build_type=settings.cmake.build_type,
            )

            builder = Builder(
                settings=settings,
                config=config,
            )

            rich_print("{green}***", "{bold}Configuring CMake...")
            # Setting the install prefix because some libs hardcode CMAKE_INSTALL_PREFIX
            # Otherwise `cmake --install --prefix` would work by itself
            defines = {"CMAKE_INSTALL_PREFIX": install_dir}
            cache_entries: dict[str, str | Path] = {
                f"SKBUILD_{k.upper()}_DIR": v for k, v in wheel_dirs.items()
            }
            cache_entries["SKBUILD_STATE"] = state
            builder.configure(
                defines=defines,
                cache_entries=cache_entries,
                name=metadata.name,
                version=metadata.version,
            )

            if exit_after_config:
                return WheelImplReturn("", settings=settings)

            default_gen = (
                "MSVC"
                if sysconfig.get_platform().startswith("win")
                else "Default Generator"
            )
            generator = builder.get_generator() or default_gen
            rich_print(
                "{green}***",
                f"{{bold}}Building project with {{blue}}{generator}{{default}}...",
            )
            build_args: list[str] = []
            builder.build(build_args=build_args)

            if not (editable and settings.editable.mode == "inplace"):
                rich_print(
                    "{green}***",
                    "{bold}Installing project into wheel...",
                )
                builder.install(install_dir)

            if not builder.config.single_config and builder.config.build_type:
                build_options += ["--config", builder.config.build_type]
                install_options += ["--config", builder.config.build_type]
            if builder.settings.cmake.verbose:
                build_options.append("-v")

        assert wheel_directory is not None

        rich_print("{green}***", f"{{bold}}Making {state}...")
        packages = _get_packages(
            packages=settings.wheel.packages,
            name=normalized_name,
        )
        mapping = packages_to_file_mapping(
            packages=packages,
            platlib_dir=wheel_dirs[targetlib],
            include=settings.sdist.include,
            src_exclude=settings.sdist.exclude,
            target_exclude=settings.wheel.exclude,
            build_dir=settings.build_dir,
        )

        if not editable:
            for filepath, package_dir in mapping.items():
                Path(package_dir).parent.mkdir(exist_ok=True, parents=True)
                shutil.copyfile(filepath, package_dir)

            process_script_dir(wheel_dirs["scripts"])

        with WheelWriter(
            metadata,
            Path(wheel_directory),
            tags.as_tags_set(),
            WheelMetadata(
                root_is_purelib=targetlib == "purelib",
                build_tag=settings.wheel.build_tag,
            ),
            wheel_dirs["metadata"],
        ) as wheel:
            wheel.build(wheel_dirs, exclude=settings.wheel.exclude)

            str_pkgs = (
                str(Path.cwd().joinpath(p).parent.resolve()) for p in packages.values()
            )
            if editable and settings.editable.mode == "redirect":
                reload_dir = build_dir.resolve() if settings.build_dir else None

                _make_editable(
                    build_options=build_options,
                    install_options=install_options,
                    libdir=wheel_dirs[targetlib],
                    mapping=mapping,
                    reload_dir=reload_dir,
                    settings=settings,
                    wheel=wheel,
                    name=normalized_name,
                    packages=str_pkgs,
                )
            elif editable and settings.editable.mode == "inplace":
                if not packages:
                    msg = "Editable inplace mode requires at least one package"
                    raise AssertionError(msg)

                wheel.writestr(
                    f"_{normalized_name}_editable.pth",
                    "\n".join(str_pkgs).encode(),
                )

    if metadata_directory is not None:
        dist_info_contents = wheel.dist_info_contents()
        dist_info = Path(metadata_directory)
        for key, data in dist_info_contents.items():
            path = dist_info / key
            prevous_data = path.read_bytes()
            if prevous_data != data:
                msg = f"Metadata mismatch in {key}"
                logger.error("{}: {!r} != {!r}", msg, prevous_data, data)
                raise AssertionError(msg)

    wheel_filename: str = wheel.wheelpath.name
    rich_print("{green}***", f"{{bold}}Created{{normal}} {wheel_filename}")
    if settings.messages.after_success:
        rich_print(settings.messages.after_success)
    return WheelImplReturn(
        wheel_filename=wheel_filename, mapping=mapping, settings=settings
    )
