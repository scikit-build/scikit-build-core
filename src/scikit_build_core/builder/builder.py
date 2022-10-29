from __future__ import annotations

import dataclasses
import re
import sys
import sysconfig
from pathlib import Path
from typing import Mapping

from packaging.version import Version

from .. import __version__
from .._logging import logger
from ..builder.macos import get_macosx_deployment_target
from ..builder.sysconfig import get_python_include_dir, get_python_library
from ..cmake import CMakeConfig
from ..errors import NinjaNotFoundError
from ..program_search import best_program, get_ninja_programs
from ..resources import find_python
from ..settings.cmake_model import ScikitBuildSettings

__all__: list[str] = ["Builder"]

DIR = Path(__file__).parent.resolve()


def __dir__() -> list[str]:
    return __all__


@dataclasses.dataclass
class Builder:
    settings: ScikitBuildSettings
    config: CMakeConfig

    # TODO: cross-compile support for other platforms
    def get_archs(self) -> list[str]:
        """
        Takes macOS platform settings and returns a list of platforms.

        Example (macOS):
            ARCHFLAGS="-arch x86_64" -> ["x86_64"]
            ARCHFLAGS="-arch x86_64 -arch arm64" -> ["x86_64", "arm64"]
            ARCHFLAGS="-arch universal2" -> ["universal2"]

        Returns an empty list otherwise or if ARCHFLAGS is not set.
        """

        if sys.platform.startswith("darwin"):
            archs = re.findall(r"-arch (\S+)", self.config.env.get("ARCHFLAGS", ""))
            return archs

        return []

    def configure(
        self,
        *,
        defines: Mapping[str, str],
        name: str | None = None,
        version: Version | None = None,
    ) -> None:
        cmake_defines = dict(defines)
        cmake_args: list[str] = []

        site_packages = Path(sysconfig.get_path("purelib"))
        self.config.prefix_dirs.append(site_packages)
        if site_packages != DIR.parent.parent:
            self.config.prefix_dirs.append(DIR.parent.parent)

        if self.config.cmake.version < Version("3.24"):
            self.config.module_dirs.append(Path(find_python.__file__).parent.resolve())

        if sys.platform.startswith("win32"):
            # TODO: support cross-compilation
            is_64bit = sys.maxsize > 2**32
            if not is_64bit:
                cmake_args += ["-A", "Win32"]
        else:
            # Ninja is currently required on Unix
            ninja = best_program(
                get_ninja_programs(),
                minimum_version=Version(self.settings.ninja.minimum_version),
            )
            if ninja is None:
                raise NinjaNotFoundError("Ninja is required to build")
            self.config.env.setdefault("CMAKE_MAKE_PROGRAM", str(ninja.path))

        cache_config: dict[str, str | Path] = {
            "SKBUILD": "2",
            "SKBUILD_CORE_VERSION": __version__,
        }

        if name is not None:
            canonical_name = name.replace("-", "_").replace(".", "_")
            cache_config["SKBUILD_PROJECT_NAME"] = canonical_name
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
        cmake_args += [
            item for item in self.config.env.get("CMAKE_ARGS", "").split(" ") if item
        ]

        if sys.platform.startswith("darwin"):
            # Cross-compile support for macOS - respect ARCHFLAGS if set
            archs = self.get_archs()
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
