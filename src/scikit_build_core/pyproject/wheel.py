from __future__ import annotations

import shutil
import sys
import tempfile
from collections.abc import Sequence
from pathlib import Path

import distlib.wheel
import packaging.utils
from packaging.version import Version
from pyproject_metadata import StandardMetadata

from .. import __version__
from .._compat import tomllib
from .._logging import logger, rich_print
from ..builder.builder import Builder
from ..builder.wheel_tag import WheelTag
from ..cmake import CMake, CMakeConfig
from ..settings.skbuild_read_settings import read_settings
from .file_processor import each_unignored_file
from .init import setup_logging

__all__: list[str] = ["build_wheel"]


def __dir__() -> list[str]:
    return __all__


class DistWheel(distlib.wheel.Wheel):  # type: ignore[misc]
    wheel_version = (1, 0)


def _copy_python_packages_to_wheel(
    *,
    packages: Sequence[str] | None,
    name: str,
    install_dir: Path,
    include: Sequence[str],
    exclude: Sequence[str],
) -> None:
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
            install_path = install_dir / filepath.relative_to(base_path)
            if not install_path.is_file():
                install_path.parent.mkdir(exist_ok=True, parents=True)
                shutil.copyfile(filepath, install_path)


def _write_wheel_metadata(
    *,
    install_dir: Path,
    metadata: StandardMetadata,
) -> None:
    name = packaging.utils.canonicalize_name(metadata.name).replace("-", "_")
    version = str(metadata.version)
    dist_info = install_dir / Path(f"{name}-{version}.dist-info")
    dist_info.mkdir(exist_ok=False)
    with dist_info.joinpath("METADATA").open("wb") as f:
        f.write(bytes(metadata.as_rfc822()))
    with dist_info.joinpath("entrypoints.txt").open("w", encoding="utf_8") as f:
        ep = metadata.entrypoints.copy()
        ep["console_scripts"] = metadata.scripts
        ep["gui_scripts"] = metadata.gui_scripts
        for group, entries in ep.items():
            if entries:
                f.write(f"[{group}]\n")
                for name, target in entries.items():
                    f.write(f"{name} = {target}\n")
                f.write("\n")


def build_wheel(
    wheel_directory: str,
    config_settings: dict[str, list[str] | str] | None = None,
    metadata_directory: str | None = None,
) -> str:
    settings = read_settings(Path("pyproject.toml"), config_settings or {})
    setup_logging(settings.logging.level)

    # We don't support preparing metadata yet
    assert metadata_directory is None

    with Path("pyproject.toml").open("rb") as ft:
        pyproject = tomllib.load(ft)
    metadata = StandardMetadata.from_pyproject(pyproject)

    if metadata.version is None:
        msg = "project.version is not statically specified, must be present currently"
        raise AssertionError(msg)

    settings = read_settings(Path("pyproject.toml"), config_settings or {})

    wheel = DistWheel()
    wheel.dirname = wheel_directory
    wheel.name = packaging.utils.canonicalize_name(metadata.name).replace("-", "_")
    wheel.version = str(metadata.version)

    cmake = CMake.default_search(
        minimum_version=Version(settings.cmake.minimum_version)
    )
    rich_print(
        f"[green]***[/green] [bold][green]scikit-build-core {__version__}[/green] using [blue]CMake {cmake.version}[/blue]"
    )

    with tempfile.TemporaryDirectory() as tmpdir:
        build_tmp_folder = Path(tmpdir)
        install_dir = build_tmp_folder / "install" / metadata.name
        build_dir = build_tmp_folder / "build"

        config = CMakeConfig(
            cmake,
            source_dir=Path("."),
            build_dir=build_dir,
        )

        builder = Builder(
            settings=settings,
            config=config,
        )

        rich_print("[green]***[/green] [bold]Configurating CMake...")
        defines: dict[str, str] = {}
        builder.configure(
            defines=defines,
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
        _copy_python_packages_to_wheel(
            packages=settings.wheel.packages,
            name=metadata.name.replace("-", "_").replace(".", "_"),
            install_dir=install_dir,
            include=settings.sdist.include,
            exclude=settings.sdist.exclude,
        )

        _write_wheel_metadata(install_dir=install_dir, metadata=metadata)

        tags = WheelTag.compute_best(builder.get_archs(), settings.tags.py_abi)
        wheel.build({"platlib": str(install_dir)}, tags=tags.tags_dict())

    wheel_filename: str = wheel.filename
    return wheel_filename
