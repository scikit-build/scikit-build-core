from __future__ import annotations

import dataclasses
import shutil
import sys
import tempfile
from collections.abc import Sequence
from pathlib import Path

from packaging.version import Version
from pyproject_metadata import StandardMetadata

from .. import __version__
from .._compat import tomllib
from .._logging import logger, rich_print
from ..builder.builder import Builder
from ..builder.wheel_tag import WheelTag
from ..cmake import CMake, CMaker
from ..settings.skbuild_read_settings import SettingsReader
from ._file_processor import each_unignored_file
from ._init import setup_logging
from ._wheelfile import WheelWriter

__all__: list[str] = ["_build_wheel_impl"]


def __dir__() -> list[str]:
    return __all__


def _copy_python_packages_to_wheel(
    *,
    packages: Sequence[str] | None,
    name: str,
    platlib_dir: Path,
    include: Sequence[str],
    exclude: Sequence[str],
) -> dict[str, str]:
    mapping = {}
    if packages is None:
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

    for package in packages:
        source_package = Path(package)
        base_path = source_package.parent
        for filepath in each_unignored_file(
            source_package,
            include=include,
            exclude=exclude,
        ):
            package_dir = platlib_dir / filepath.relative_to(base_path)
            if not package_dir.is_file():
                package_dir.parent.mkdir(exist_ok=True, parents=True)
                shutil.copyfile(filepath, package_dir)
                mapping[str(filepath)] = str(package_dir)

    return mapping


@dataclasses.dataclass
class WheelImplReturn:
    wheel_filename: str
    mapping: dict[str, str] = dataclasses.field(default_factory=dict)


def _build_wheel_impl(
    wheel_directory: str | None,
    config_settings: dict[str, list[str] | str] | None = None,
    metadata_directory: str | None = None,
) -> WheelImplReturn:
    """
    Build a wheel or just prepare metadata (if wheel dir is None).
    """

    settings_reader = SettingsReader(Path("pyproject.toml"), config_settings or {})
    settings = settings_reader.settings
    setup_logging(settings.logging.level)

    settings_reader.validate_may_exit()

    with Path("pyproject.toml").open("rb") as ft:
        pyproject = tomllib.load(ft)
    metadata = StandardMetadata.from_pyproject(pyproject)

    if metadata.version is None:
        msg = "project.version is not statically specified, must be present currently"
        raise AssertionError(msg)

    cmake = CMake.default_search(
        minimum_version=Version(settings.cmake.minimum_version)
    )
    rich_print(
        f"[green]***[/green] [bold][green]scikit-build-core {__version__}[/green] using [blue]CMake {cmake.version}[/blue]"
    )

    with tempfile.TemporaryDirectory() as tmpdir:
        build_tmp_folder = Path(tmpdir)
        wheel_dir = build_tmp_folder / "wheel"

        # A build dir can be specified, otherwise use a temporary directory
        build_dir = (
            Path(settings.build_dir.format(cache_tag=sys.implementation.cache_tag))
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

        config = CMaker(
            cmake,
            source_dir=Path("."),
            build_dir=build_dir,
            build_type=settings.cmake.build_type,
        )

        builder = Builder(
            settings=settings,
            config=config,
        )

        tags = WheelTag.compute_best(
            builder.get_arch_tags(),
            settings.wheel.py_api,
            expand_macos=settings.wheel.expand_macos_universal_tags,
        )

        if wheel_directory is None:
            if metadata_directory is None:
                msg = "metadata_directory must be specified if wheel_directory is None"
                raise AssertionError(msg)
            with WheelWriter(
                metadata, Path(metadata_directory), tags.as_tags_set()
            ) as wheel:
                dist_info_contents = wheel.dist_info_contents()
                dist_info = Path(metadata_directory) / f"{wheel.name_ver}.dist-info"
                dist_info.mkdir(parents=True)
                for key, data in dist_info_contents.items():
                    path = dist_info / key
                    path.write_bytes(data)
            return WheelImplReturn(wheel_filename=dist_info.name)

        rich_print("[green]***[/green] [bold]Configurating CMake...")
        defines: dict[str, str] = {}
        cache_entries = {f"SKBUILD_{k.upper()}_DIR": v for k, v in wheel_dirs.items()}
        builder.configure(
            defines=defines,
            cache_entries=cache_entries,
            name=metadata.name,
            version=metadata.version,
        )

        generator = builder.config.env.get(
            "CMAKE_GENERATOR", "MSVC" if sys.platform.startswith("win32") else "Unknown"
        )
        rich_print(
            f"[green]***[/green] [bold]Building project with [blue]{generator}[/blue]..."
        )
        build_args: list[str] = []
        builder.build(build_args=build_args)

        rich_print("[green]***[/green] [bold]Installing project into wheel...")
        builder.install(install_dir)

        rich_print("[green]***[/green] [bold]Making wheel...")
        mapping = _copy_python_packages_to_wheel(
            packages=settings.wheel.packages,
            name=metadata.name.replace("-", "_").replace(".", "_"),
            platlib_dir=wheel_dirs["platlib"],
            include=settings.sdist.include,
            exclude=settings.sdist.exclude,
        )

        for item in wheel_dirs["scripts"].iterdir():
            with item.open("rb") as f:
                content = f.read(len(b"#!python"))
                if content.startswith(b"#!/") and content == b"#!python":
                    logger.warning(
                        "Files in scripts/ are not post-processed yet for shabang fixes"
                    )
                    break

        with WheelWriter(metadata, Path(wheel_directory), tags.as_tags_set()) as wheel:
            wheel.build(wheel_dirs)

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
    return WheelImplReturn(wheel_filename=wheel_filename, mapping=mapping)
