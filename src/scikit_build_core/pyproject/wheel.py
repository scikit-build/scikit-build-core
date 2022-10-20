from __future__ import annotations

import shutil
import sys
import tempfile
from pathlib import Path

import distlib.wheel
import packaging.tags
import packaging.utils
from packaging.version import Version
from pyproject_metadata import StandardMetadata

from .._compat import tomllib
from ..builder.builder import Builder
from ..builder.cmake_module_dirs import get_cmake_modules
from ..builder.macos import get_macosx_deployment_target
from ..cmake import CMake, CMakeConfig
from ..settings.skbuild_settings import read_settings

__all__: list[str] = ["build_wheel"]


def __dir__() -> list[str]:
    return __all__


def build_wheel(
    wheel_directory: str,
    config_settings: dict[str, list[str] | str] | None = None,
    metadata_directory: str | None = None,
) -> str:

    # We don't support preparing metadata yet
    assert metadata_directory is None

    with Path("pyproject.toml").open("rb") as ft:
        pyproject = tomllib.load(ft)
    metadata = StandardMetadata.from_pyproject(pyproject)

    if metadata.version is None:
        raise AssertionError(
            "project.version is not statically specified, must be present currently"
        )

    settings = read_settings(Path("pyproject.toml"), config_settings or {})

    best_tag = next(packaging.tags.sys_tags())
    interp, abi, plat = (best_tag.interpreter, best_tag.abi, best_tag.platform)
    if sys.platform.startswith("darwin"):
        str_target = get_macosx_deployment_target()
        min_macos, max_macos = str_target.split(".")
        plat = next(packaging.tags.mac_platforms((int(min_macos), int(max_macos))))

    distlib.wheel.Wheel.wheel_version = (1, 0)
    wheel = distlib.wheel.Wheel()
    wheel.name = packaging.utils.canonicalize_name(metadata.name).replace("-", "_")
    wheel.version = str(metadata.version)
    tags = {
        "pyver": [interp],
        "abi": [abi],
        "arch": [plat],
    }

    cmake = CMake.default_search(
        minimum_version=Version(settings.cmake.minimum_version)
    )

    def select(name: str) -> bool:
        return name != "find-python" or cmake.version < Version("3.24")

    with tempfile.TemporaryDirectory() as tmpdir:
        build_tmp_folder = Path(tmpdir)
        install_dir = build_tmp_folder / "install" / metadata.name
        build_dir = build_tmp_folder / "build"

        config = CMakeConfig(
            cmake,
            source_dir=Path("."),
            build_dir=build_dir,
            module_dirs=get_cmake_modules(select),
        )

        builder = Builder(
            settings=settings,
            config=config,
        )

        defines: dict[str, str] = {}
        builder.configure(
            defines=defines,
            ext_dir=install_dir,
            name=metadata.name,
            version=metadata.version,
        )

        build_args: list[str] = []
        builder.build(build_args=build_args)

        builder.install(install_dir)

        dist_info = install_dir / Path(f"{wheel.name}-{wheel.version}.dist-info")
        dist_info.mkdir(exist_ok=False)
        with dist_info.joinpath("METADATA").open("wb") as f:
            f.write(bytes(metadata.as_rfc822()))
        with dist_info.joinpath("entry-points.txt").open("wb") as f:
            # TODO: implement
            f.write(b"")

        out = wheel.build({"platlib": str(install_dir)}, tags=tags)
        shutil.move(out, wheel_directory)

    wheel_filename: str = wheel.filename
    return wheel_filename
