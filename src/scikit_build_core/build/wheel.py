from __future__ import annotations

import dataclasses
import os
import shutil
import sys
import sysconfig
import tempfile
from collections.abc import Sequence
from pathlib import Path

from packaging.version import Version

from .. import __version__
from .._compat import tomllib
from .._logging import logger, rich_print
from .._shutil import fix_win_37_all_permissions
from ..builder.builder import Builder, archs_to_tags, get_archs
from ..builder.wheel_tag import WheelTag
from ..cmake import CMake, CMaker
from ..resources import resources
from ..settings.metadata import get_standard_metadata
from ..settings.skbuild_read_settings import SettingsReader
from ._init import setup_logging
from ._pathutil import packages_to_file_mapping, path_to_module, scantree
from ._scripts import process_script_dir
from ._wheelfile import WheelWriter

__all__: list[str] = ["_build_wheel_impl"]


def __dir__() -> list[str]:
    return __all__


def _get_packages(
    *,
    packages: Sequence[str] | None,
    name: str,
) -> list[str]:
    if packages is not None:
        return list(packages)

    # Auto package discovery
    packages = []
    for base_path in (Path("src"), Path(".")):
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
    editable: bool,
) -> WheelImplReturn:
    """
    Build a wheel or just prepare metadata (if wheel dir is None). Can be editable.
    """
    pyproject_path = Path("pyproject.toml")
    with pyproject_path.open("rb") as ft:
        pyproject = tomllib.load(ft)

    settings_reader = SettingsReader(pyproject, config_settings or {})
    settings = settings_reader.settings
    setup_logging(settings.logging.level)

    settings_reader.validate_may_exit()

    metadata = get_standard_metadata(pyproject, settings)

    if metadata.version is None:
        msg = "project.version is not statically specified, must be present currently"
        raise AssertionError(msg)

    normalized_name = metadata.name.replace("-", "_").replace(".", "_")

    action = "editable" if editable else "wheel"
    if wheel_directory is None:
        action = f"metadata_{action}"

    cmake = CMake.default_search(
        minimum_version=Version(settings.cmake.minimum_version)
    )

    rich_print(
        f"[green]***[/green] [bold][green]scikit-build-core {__version__}[/green]",
        f"using [blue]CMake {cmake.version}[/blue]",
        f"[red]({action})[/red]",
    )

    with tempfile.TemporaryDirectory() as tmpdir, fix_win_37_all_permissions(tmpdir):
        build_tmp_folder = Path(tmpdir)
        wheel_dir = build_tmp_folder / "wheel"

        tags = WheelTag.compute_best(
            archs_to_tags(get_archs(os.environ)),
            settings.wheel.py_api,
            expand_macos=settings.wheel.expand_macos_universal_tags,
        )

        # A build dir can be specified, otherwise use a temporary directory
        build_dir = (
            Path(
                settings.build_dir.format(
                    cache_tag=sys.implementation.cache_tag,
                    wheel_tag=str(tags),
                )
            )
            if settings.build_dir
            else build_tmp_folder / "build"
        )
        logger.info("Build directory: {}", build_dir.resolve())

        wheel_dirs = {
            "platlib": wheel_dir / "platlib",
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
            install_dir = wheel_dirs["platlib"] / settings.wheel.install_dir

        license_files = {
            x: x.read_bytes()
            for y in settings.wheel.license_files
            for x in Path().glob(y)
        }
        if settings.wheel.license_files and not license_files:
            logger.warning(
                "No license files found, set wheel.license-files to [] to suppress this warning"
            )

        config = CMaker(
            cmake,
            source_dir=Path(settings.cmake.source_dir or "."),
            build_dir=build_dir,
            build_type=settings.cmake.build_type,
        )

        builder = Builder(
            settings=settings,
            config=config,
        )

        if wheel_directory is None:
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

        rich_print("[green]***[/green] [bold]Configuring CMake...")
        defines: dict[str, str] = {}
        cache_entries: dict[str, str | Path] = {
            f"SKBUILD_{k.upper()}_DIR": v for k, v in wheel_dirs.items()
        }
        cache_entries["SKBUILD_STATE"] = action
        builder.configure(
            defines=defines,
            cache_entries=cache_entries,
            name=metadata.name,
            version=metadata.version,
        )

        generator = builder.config.env.get(
            "CMAKE_GENERATOR",
            "MSVC"
            if sysconfig.get_platform().startswith("win")
            else "Default generator",
        )
        rich_print(
            f"[green]***[/green] [bold]Building project with [blue]{generator}[/blue]..."
        )
        build_args: list[str] = []
        builder.build(build_args=build_args)

        rich_print("[green]***[/green] [bold]Installing project into wheel...")
        builder.install(install_dir)

        rich_print(f"[green]***[/green] [bold]Making {action}...")
        packages = _get_packages(
            packages=settings.wheel.packages,
            name=normalized_name,
        )
        mapping = packages_to_file_mapping(
            packages=packages,
            platlib_dir=wheel_dirs["platlib"],
            include=settings.sdist.include,
            exclude=settings.sdist.exclude,
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

            if editable:
                modules = {
                    path_to_module(Path(v).relative_to(wheel_dirs["platlib"])): str(
                        Path(k).resolve()
                    )
                    for k, v in mapping.items()
                }
                installed = {
                    path_to_module(v.relative_to(wheel_dirs["platlib"])): str(
                        v.relative_to(wheel_dirs["platlib"])
                    )
                    for v in scantree(wheel_dirs["platlib"])
                }
                editable_py = resources / "_editable_redirect.py"
                editable_txt = editable_py.read_text(encoding="utf-8")
                reload_dir = (
                    os.fspath(build_dir.resolve()) if settings.build_dir else None
                )
                options = []
                if not builder.config.single_config and builder.config.build_type:
                    options += ["--config", builder.config.build_type]
                ext_build_opts = ["-v"] if builder.settings.cmake.verbose else []

                arguments = (
                    modules,
                    installed,
                    reload_dir,
                    settings.editable.rebuild,
                    settings.editable.verbose,
                    options + ext_build_opts,
                    options,
                )
                arguments_str = ", ".join(repr(x) for x in arguments)
                editable_txt += f"\n\ninstall({arguments_str})\n"

                wheel.writestr(
                    f"_{normalized_name}_editable.py",
                    editable_txt.encode("utf-8"),
                )
                wheel.writestr(
                    f"_{normalized_name}_editable.pth",
                    f"import _{normalized_name}_editable\n".encode(),
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
