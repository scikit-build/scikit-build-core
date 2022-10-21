from __future__ import annotations

import dataclasses
import os
import re
import sys
import sysconfig
from pathlib import Path
from typing import Mapping

from packaging.version import Version

from scikit_build_core.settings.cmake_model import ScikitBuildSettings

from .._logging import logger
from ..builder.macos import get_macosx_deployment_target
from ..builder.sysconfig import get_python_include_dir, get_python_library
from ..cmake import CMakeConfig
from ..errors import NinjaNotFoundError
from ..program_search import best_program, get_ninja_programs

__all__: list[str] = ["Builder"]

DIR = Path(__file__).parent.resolve()


def __dir__() -> list[str]:
    return __all__


@dataclasses.dataclass
class Builder:
    settings: ScikitBuildSettings
    config: CMakeConfig

    def configure(
        self,
        *,
        defines: Mapping[str, str],
        ext_dir: Path,
        name: str | None = None,
        version: Version | None = None,
    ) -> None:
        cmake_defines = dict(defines)

        site_packages = Path(sysconfig.get_path("purelib"))
        self.config.prefix_dirs = [site_packages]
        if site_packages != DIR.parent.parent:
            self.config.prefix_dirs.append(DIR.parent.parent)

        # Ninja is currently required on Unix
        if not sys.platform.startswith("win32"):
            ninja = best_program(
                get_ninja_programs(),
                minimum_version=Version(self.settings.ninja.minimum_version),
            )
            if ninja is None:
                raise NinjaNotFoundError("Ninja is required to build")
            self.config.env.setdefault("CMAKE_MAKE_PROGRAM", str(ninja.path))

        cache_config: dict[str, str | Path] = {
            "CMAKE_LIBRARY_OUTPUT_DIRECTORY": f"{ext_dir}{os.path.sep}",
            "SKBUILD": "2",
        }
        if sys.platform.startswith("win32"):
            cache_config[
                f"CMAKE_LIBRARY_OUTPUT_DIRECTORY_{self.config.build_type.upper()}"
            ] = f"{ext_dir}{os.path.sep}"

        if name is not None:
            cache_config["SKBUILD_PROJECT_NAME"] = name
        if version is not None:
            cache_config["SKBUILD_PROJECT_VERSION"] = str(version)

        # Classic Find Python
        python_library = get_python_library()
        python_include_dir = get_python_include_dir()
        cache_config["PYTHON_EXECUTABLE"] = sys.executable
        cache_config["PYTHON_INCLUDE_DIR"] = python_include_dir
        if python_library:
            cache_config["PYTHON_LIBRARY"] = python_library

        # Modern Find Python
        for prefix in ["Python", "Python3"]:
            cache_config[f"{prefix}_EXECUTABLE"] = sys.executable
            cache_config[f"{prefix}_ROOT_DIR"] = sys.prefix
            cache_config[f"{prefix}_FIND_REGISTRY"] = "NEVER"

        self.config.init_cache(cache_config)

        # Adding CMake arguments set as environment variable
        # (needed e.g. to build for ARM OSX on conda-forge)
        cmake_args = [
            item for item in self.config.env.get("CMAKE_ARGS", "").split(" ") if item
        ]

        if sys.platform.startswith("darwin"):
            # Cross-compile support for macOS - respect ARCHFLAGS if set
            archs = re.findall(r"-arch (\S+)", self.config.env.get("ARCHFLAGS", ""))
            if archs:
                cmake_defines["CMAKE_OSX_ARCHITECTURES"] = ";".join(archs)

            self.config.env.setdefault(
                "MACOSX_DEPLOYMENT_TARGET", get_macosx_deployment_target()
            )
            logger.info(
                "MACOSX_DEPLOYMENT_TARGET is {}",
                self.config.env["MACOSX_DEPLOYMENT_TARGET"],
            )

        self.config.configure(
            defines=cmake_defines,
            cmake_args=cmake_args,
        )

    def build(self, build_args: list[str]) -> None:
        # TODO: configure verbose
        self.config.build(build_args=build_args, verbose=1)

    def install(self, install_dir: Path) -> None:
        self.config.install(install_dir)
