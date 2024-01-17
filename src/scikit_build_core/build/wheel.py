from __future__ import annotations

import dataclasses
import os
import shutil
import sys
import sysconfig
import tempfile
from pathlib import Path
from typing import TYPE_CHECKING

from .. import __version__
from .._compat import tomllib
from .._compat.typing import Literal, assert_never
from .._logging import logger, rich_print
from .._shutil import fix_win_37_all_permissions
from ..builder.builder import Builder, archs_to_tags, get_archs
from ..builder.wheel_tag import WheelTag
from ..cmake import CMake, CMaker
from ..settings.metadata import get_standard_metadata
from ..settings.skbuild_read_settings import SettingsReader
from ._editable import editable_redirect, libdir_to_installed, mapping_to_modules
from ._init import setup_logging
from ._pathutil import (
    packages_to_file_mapping,
)
from ._scripts import process_script_dir
from ._wheelfile import WheelWriter
from .generate import generate_file_contents

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

    editable_txt = editable_redirect(
        modules=modules,
        installed=installed,
        reload_dir=reload_dir,
        rebuild=settings.editable.rebuild,
        verbose=settings.editable.verbose,
        build_options=build_options,
        install_options=install_options,
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
    packages: Sequence[str] | None,
    name: str,
) -> list[str]:
    if packages is not None:
        return list(packages)

    # Auto package discovery
    packages = []
    for base_path in (Path("src"), Path("python"), Path()):
        path = base_path / name
        if path.is_dir() and (
            (path / "__init__.py").is_file() or (path / "__init__.pyi").is_file()
        ):
            logger.info("Discovered Python package at {}", path)
            packages += [str(path)]
            break
    else:
        logger.debug("Didn't find a Python package for {}", name)

    return packages


@dataclasses.dataclass
class WheelImplReturn:
    wheel_filename: str
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

    settings_reader = SettingsReader(pyproject, config_settings or {}, state=state)
    settings = settings_reader.settings
    setup_logging(settings.logging.level)

    settings_reader.validate_may_exit()

    metadata = get_standard_metadata(pyproject, settings)

    if metadata.version is None:
        msg = "project.version is not statically specified, must be present currently"
        raise AssertionError(msg)

    normalized_name = metadata.name.replace("-", "_").replace(".", "_")

    if settings.wheel.cmake:
        cmake = CMake.default_search(version=settings.cmake.version)
        cmake_msg = [f"using [blue]CMake {cmake.version}[/blue]"]
    else:
        cmake = None
        cmake_msg = []

    if settings.wheel.platlib is None:
        targetlib = "platlib" if settings.wheel.cmake else "purelib"
    else:
        targetlib = "platlib" if settings.wheel.platlib else "purelib"

    rich_print(
        f"[green]***[/green] [bold][green]scikit-build-core {__version__}[/green]",
        *cmake_msg,
        f"[red]({state})[/red]",
    )

    with tempfile.TemporaryDirectory() as tmpdir, fix_win_37_all_permissions(tmpdir):
        build_tmp_folder = Path(tmpdir)
        wheel_dir = build_tmp_folder / "wheel"

        tags = WheelTag.compute_best(
            archs_to_tags(get_archs(os.environ)),
            settings.wheel.py_api,
            expand_macos=settings.wheel.expand_macos_universal_tags,
            build_tag=settings.wheel.build_tag,
        )

        # A build dir can be specified, otherwise use a temporary directory
        build_dir = (
            Path(
                settings.build_dir.format(
                    cache_tag=sys.implementation.cache_tag,
                    wheel_tag=str(tags),
                    build_type=settings.cmake.build_type,
                    state=state,
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
        license_file_globs = list(settings.wheel.license_files)
        if metadata.license and metadata.license.file:
            license_file_globs.append(str(metadata.license.file))

        license_files = {
            x: x.read_bytes()
            for y in license_file_globs
            for x in Path().glob(y)
            if x.is_file()
        }
        if settings.wheel.license_files and not license_files:
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
                license_files=license_files,
            )
            dist_info_contents = wheel.dist_info_contents()
            dist_info = Path(metadata_directory) / f"{wheel.name_ver}.dist-info"
            dist_info.mkdir(parents=True)
            for key, data in dist_info_contents.items():
                path = dist_info / key
                if not path.parent.is_dir():
                    path.parent.mkdir(exist_ok=True, parents=True)
                path.write_bytes(data)
            return WheelImplReturn(wheel_filename=dist_info.name)

        for gen in settings.generate:
            contents = generate_file_contents(gen, metadata)
            if gen.location == "source":
                continue
            if gen.location == "build":
                path = build_dir / gen.path
            elif gen.location == "install":
                path = install_dir / gen.path
            else:
                assert_never(gen.location)
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(contents, encoding="utf-8")

        build_options = []
        install_options = []

        if cmake is not None:
            if editable and settings.editable.mode == "inplace":
                build_dir = settings.cmake.source_dir
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

            rich_print("[green]***[/green] [bold]Configuring CMake...")
            defines: dict[str, str] = {}
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
                return WheelImplReturn("")

            default_gen = (
                "MSVC"
                if sysconfig.get_platform().startswith("win")
                else "Default Generator"
            )
            generator = builder.get_generator() or default_gen
            rich_print(
                f"[green]***[/green] [bold]Building project with [blue]{generator}[/blue]..."
            )
            build_args: list[str] = []
            builder.build(build_args=build_args)

            if not (editable and settings.editable.mode == "inplace"):
                rich_print("[green]***[/green] [bold]Installing project into wheel...")
                builder.install(install_dir)

            if not builder.config.single_config and builder.config.build_type:
                build_options += ["--config", builder.config.build_type]
                install_options += ["--config", builder.config.build_type]
            if builder.settings.cmake.verbose:
                build_options.append("-v")

        assert wheel_directory is not None

        rich_print(f"[green]***[/green] [bold]Making {state}...")
        packages = _get_packages(
            packages=settings.wheel.packages,
            name=normalized_name,
        )
        mapping = packages_to_file_mapping(
            packages=packages,
            platlib_dir=wheel_dirs[targetlib],
            include=settings.sdist.include,
            exclude=[*settings.sdist.exclude, *settings.wheel.exclude],
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
            license_files=license_files,
        ) as wheel:
            wheel.build(wheel_dirs)

            str_pkgs = (str(Path.cwd().joinpath(p).parent.resolve()) for p in packages)
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
    rich_print(f"[green]***[/green] [bold]Created[/bold] {wheel_filename}...")
    return WheelImplReturn(wheel_filename=wheel_filename, mapping=mapping)
