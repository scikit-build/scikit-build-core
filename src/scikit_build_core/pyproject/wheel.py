from __future__ import annotations

import shutil
import tempfile
from pathlib import Path

import distlib.wheel
import packaging.utils
from packaging.version import Version
from pyproject_metadata import StandardMetadata

from .._compat import tomllib
from ..builder.builder import Builder
from ..builder.wheel_tag import WheelTag
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
        msg = "project.version is not statically specified, must be present currently"
        raise AssertionError(msg)

    settings = read_settings(Path("pyproject.toml"), config_settings or {})

    distlib.wheel.Wheel.wheel_version = (1, 0)
    wheel = distlib.wheel.Wheel()
    wheel.name = packaging.utils.canonicalize_name(metadata.name).replace("-", "_")
    wheel.version = str(metadata.version)

    cmake = CMake.default_search(
        minimum_version=Version(settings.cmake.minimum_version)
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
        tags = WheelTag.compute_best(builder.get_archs())

        defines: dict[str, str] = {}
        builder.configure(
            defines=defines,
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

        out = wheel.build({"platlib": str(install_dir)}, tags=tags.tags_dict())
        shutil.move(out, wheel_directory)

    wheel_filename: str = wheel.filename
    return wheel_filename
