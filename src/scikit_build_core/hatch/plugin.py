# pylint: disable=duplicate-code

from __future__ import annotations

import copy
import importlib.metadata
import os
import shutil
import sysconfig
import tempfile
import typing
from pathlib import Path
from typing import Any

from hatchling.builders.hooks.plugin.interface import BuildHookInterface
from packaging.version import Version

from scikit_build_core.settings.skbuild_model import ScikitBuildSettings

from .._logging import logger, rich_print
from ..build._init import setup_logging
from ..builder.builder import Builder, archs_to_tags, get_archs
from ..builder.get_requires import GetRequires
from ..builder.wheel_tag import WheelTag
from ..cmake import CMake, CMaker
from ..format import pyproject_format
from ..settings.skbuild_read_settings import SettingsReader

__all__ = ["ScikitBuildHook"]


def __dir__() -> list[str]:
    return __all__


class ScikitBuildHook(BuildHookInterface):  # type: ignore[type-arg]
    PLUGIN_NAME = "scikit-build"

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.__tmp_dir: Path | None = None

    def _read_config(self) -> SettingsReader:
        config_dict = copy.deepcopy(self.config)
        config_dict.pop("dependencies", None)
        config_dict.pop("require-runtime-dependencies", None)
        config_dict.pop("require-runtime-features", None)

        state = typing.cast(
            "typing.Literal['sdist', 'wheel', 'editable']", self.target_name
        )
        return SettingsReader.from_file(
            "pyproject.toml", state=state, extra_settings=config_dict
        )

    def _validate(self, settings_reader: SettingsReader) -> None:
        settings = settings_reader.settings

        settings_reader.validate_may_exit()

        if not settings.experimental:
            msg = "Hatch support is experimental, must enable the experimental flag"
            raise ValueError(msg)

        if not settings.wheel.cmake or settings.sdist.cmake:
            msg = "CMake is required for scikit-build"
            raise ValueError(msg)

        if settings.sdist.include or settings.sdist.exclude:
            msg = "include and exclude are not supported for hatch builds"
            raise ValueError(msg)

        if settings.sdist.cmake:
            msg = "Not currently supported for SDist builds"
            raise ValueError(msg)

        if settings.wheel.packages:
            msg = f"Packages ({settings.wheel.packages!r}) are not supported for hatch builds"
            raise ValueError(msg)

        if (
            settings.wheel.license_files
            and settings.wheel.license_files
            != ScikitBuildSettings().wheel.license_files
        ):
            msg = f"License files ({settings.wheel.license_files!r}) are not supported for hatch builds"
            raise ValueError(msg)

        if settings.wheel.platlib is not None and not settings.wheel.platlib:
            msg = "Purelib builds not supported for hatch builds"
            raise ValueError(msg)

        if settings.generate:
            msg = "Generate is not supported for hatch builds"
            raise ValueError(msg)

        if settings.metadata:
            msg = "Metadata is not supported for hatch builds"
            raise ValueError(msg)

    # Requires Hatchling 1.22.0 to have an effect
    def dependencies(self) -> list[str]:
        settings = self._read_config().settings
        requires = GetRequires(settings)

        if self.target_name == "sdist":
            required = requires.settings.sdist.cmake
        elif self.target_name == "wheel":
            required = requires.settings.wheel.cmake
        else:
            msg = f"Unknown target: {self.target_name!r}, only 'sdist' and 'wheel' are supported"
            raise ValueError(msg)

        # These are only injected if cmake is required
        cmake_requires = [*requires.cmake(), *requires.ninja()] if required else []
        return [*cmake_requires, *requires.dynamic_metadata()]

    def initialize(self, version: str, build_data: dict[str, Any]) -> None:
        if version == "editable":
            msg = "Editable installs are not yet supported"
            raise ValueError(msg)

        self.__tmp_dir = Path(tempfile.mkdtemp()).resolve()
        try:
            self._initialize(build_data=build_data)
        except Exception:
            self._cleanup()
            raise

    def _initialize(self, *, build_data: dict[str, Any]) -> None:
        settings_reader = self._read_config()
        settings = settings_reader.settings
        state = settings_reader.state

        self._validate(settings_reader)

        if state == "sdist":
            build_data["artifacts"].append("CMakeLists.txt")  # Needs full list, etc.
            return

        setup_logging(settings.logging.level)

        cmake = CMake.default_search(version=settings.cmake.version, env=os.environ)

        rich_print(
            "{green}***",
            "{bold.green}scikit-build-core {__version__}",
            f"using {{blue}}CMake {cmake.version}",
            f"{{red}}({state})",
        )

        self.__tmp_dir = Path(tempfile.mkdtemp()).resolve()
        wheel_dir = self.__tmp_dir / "wheel"

        tags = WheelTag.compute_best(
            archs_to_tags(get_archs(os.environ)),
            settings.wheel.py_api,
            expand_macos=settings.wheel.expand_macos_universal_tags,
            build_tag=settings.wheel.build_tag,
        )
        build_data["tag"] = str(tags)
        build_data["pure_python"] = not settings.wheel.platlib

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
            else self.__tmp_dir / "build"
        )
        logger.info("Build directory: {}", build_dir.resolve())

        targetlib = "platlib"

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
        cache_entries["SKBUILD_HATCHLING"] = importlib.metadata.version("hatchling")
        builder.configure(
            defines=defines,
            cache_entries=cache_entries,
            name=self.build_config.builder.metadata.name,
            version=Version(self.build_config.builder.metadata.version),
        )

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

        rich_print("{green}***", "{bold}Installing project into wheel...")
        builder.install(install_dir)

        files = list(wheel_dirs["headers"].iterdir())
        if files:
            msg = (
                f"Unsupported files found in 'headers' directory: {files}\n"
                "Please report use case to https://github.com/pypa/hatch/issues/1291 if you need it."
            )
            raise ValueError(msg)

        for path in wheel_dirs[targetlib].iterdir():
            build_data["force_include"][f"{path}"] = str(
                settings.wheel.install_dir / path.relative_to(wheel_dirs[targetlib])
            )

        try:
            for path in wheel_dirs["data"].iterdir():
                build_data["shared_data"][f"{path.resolve()}"] = str(
                    path.relative_to(wheel_dirs["data"])
                )
        except KeyError:
            logger.error("SKBUILD_DATA_DIR not supported by Hatchling < 1.24.0")
            raise

        try:
            for path in wheel_dirs["scripts"].iterdir():
                build_data["shared_scripts"][f"{path.resolve()}"] = str(
                    path.relative_to(wheel_dirs["scripts"])
                )
        except KeyError:
            logger.error("SKBUILD_SCRIPTS_DIR not supported by Hatchling < 1.24.0")
            raise

        for path_root in wheel_dirs["metadata"].iterdir():
            if path_root.name != "extra_metadata":
                msg = f"Hatchling metadata must be in an extra_metadata folder, got {path_root}"
                raise ValueError(msg)
            for path in path_root.iterdir():
                location = path.relative_to(path_root)
                try:
                    build_data["extra_metadata"][f"{path.resolve()}"] = str(location)
                except KeyError:
                    logger.error("SKBUILD_METADATA_DIR needs a newer Hatchling")
                    raise

    def finalize(
        self, version: str, build_data: dict[str, Any], artifact_path: str
    ) -> None:
        self._cleanup()
        return super().finalize(version, build_data, artifact_path)

    def _cleanup(self) -> None:
        if self.__tmp_dir:
            shutil.rmtree(self.__tmp_dir, ignore_errors=True)
            self.__tmp_dir = None
