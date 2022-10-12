from __future__ import annotations

import os
import re
import shutil
import sys
from pathlib import Path

import setuptools
import setuptools.command.build_ext
from packaging.version import Version

from .._logging import logger
from ..builder.macos import get_macosx_deployment_target
from ..builder.sysconfig import get_python_include_dir, get_python_library
from ..cmake import CMake, CMakeConfig
from ..errors import NinjaNotFoundError
from ..program_search import best_program, get_ninja_programs
from ..settings.skbuild_settings import read_settings

__all__: list[str] = ["CMakeExtension"]


def __dir__() -> list[str]:
    return __all__


# Convert distutils Windows platform specifiers to CMake -A arguments
PLAT_TO_CMAKE = {
    "win32": "Win32",
    "win-amd64": "x64",
    "win-arm32": "ARM",
    "win-arm64": "ARM64",
}


# A CMakeExtension needs a sourcedir instead of a file list.
# The name must be the _single_ output extension from the CMake build.
# The sourcedir is relative to the setup.py directory, where the CMakeLists.txt lives
class CMakeExtension(setuptools.Extension):
    def __init__(self, name: str, sourcedir: str = "", **kwargs: object) -> None:
        setuptools.Extension.__init__(self, name, sources=[], **kwargs)
        self.sourcedir = Path(sourcedir).resolve()


class CMakeBuild(setuptools.command.build_ext.build_ext):
    def build_extension(self, ext: setuptools.Extension) -> None:
        if not isinstance(ext, CMakeExtension):
            super().build_extension(ext)
            return

        settings = read_settings(Path("pyproject.toml"), {})

        # This dir doesn't exist, so Path.cwd() is needed for Python < 3.10
        # due to a Windows bug in resolve https://github.com/python/cpython/issues/82852
        ext_fullpath = Path.cwd() / self.get_ext_fullpath(ext.name)  # type: ignore[no-untyped-call]
        extdir = ext_fullpath.parent.resolve()

        build_tmp_folder = Path(self.build_temp)
        install_dir = build_tmp_folder / ext.name
        build_temp = build_tmp_folder / "_skbuild"  # TODO: include python platform

        # TODO: this is a hack due to moving temporary paths for isolation
        if build_temp.exists():
            shutil.rmtree(build_temp)

        cmake = CMake.default_search(
            minimum_version=Version(settings.cmake.minimum_version)
        )
        config = CMakeConfig(
            cmake,
            source_dir=ext.sourcedir,
            build_dir=build_temp,
        )

        debug = int(os.environ.get("DEBUG", 0)) if self.debug is None else self.debug
        config.build_type = "Debug" if debug else "Release"

        # Ninja is currently required on Unix
        if not sys.platform.startswith("win32"):
            ninja = best_program(
                get_ninja_programs(),
                minimum_version=Version(settings.ninja.minimum_version),
            )
            if ninja is None:
                raise NinjaNotFoundError("Ninja is required to build")
            config.env.setdefault("CMAKE_MAKE_PROGRAM", str(ninja.path))

        cache_config: dict[str, str | Path] = {
            "CMAKE_LIBRARY_OUTPUT_DIRECTORY": f"{extdir}{os.path.sep}",
            "SKBUILD": "2",
        }
        if sys.platform.startswith("win32"):
            cache_config[
                f"CMAKE_LIBRARY_OUTPUT_DIRECTORY_{config.build_type.upper()}"
            ] = f"{extdir}{os.path.sep}"

        python_library = get_python_library()
        python_include_dir = get_python_include_dir()

        for prefix in ["Python", "Python3", "PYTHON"]:
            cache_config[f"{prefix}_EXECUTABLE"] = sys.executable
            cache_config[f"{prefix}_INCLUDE_DIR"] = python_include_dir
            if python_library:
                cache_config[f"{prefix}_LIBRARY"] = python_library

        config.init_cache(cache_config)

        # Adding CMake arguments set as environment variable
        # (needed e.g. to build for ARM OSx on conda-forge)
        cmake_args = [
            item for item in config.env.get("CMAKE_ARGS", "").split(" ") if item
        ]
        defines: dict[str, str] = {}

        if sys.platform.startswith("darwin"):
            # Cross-compile support for macOS - respect ARCHFLAGS if set
            archs = re.findall(r"-arch (\S+)", config.env.get("ARCHFLAGS", ""))
            if archs:
                defines["CMAKE_OSX_ARCHITECTURES"] = ";".join(archs)

            config.env.setdefault(
                "MACOSX_DEPLOYMENT_TARGET", get_macosx_deployment_target()
            )
            logger.info(
                "MACOSX_DEPLOYMENT_TARGET is {}", config.env["MACOSX_DEPLOYMENT_TARGET"]
            )

        for key, value in ext.define_macros:
            assert isinstance(value, str), "define_macros values must not be None"
            defines[key] = value

        config.configure(
            defines=defines,
            cmake_args=cmake_args,
        )

        # Set CMAKE_BUILD_PARALLEL_LEVEL to control the parallel build level
        # across all generators.
        build_args = []
        if "CMAKE_BUILD_PARALLEL_LEVEL" not in config.env:
            # self.parallel is a Python 3 only way to set parallel jobs by hand
            # using -j in the build_ext call, not supported by pip or PyPA-build.
            if hasattr(self, "parallel") and self.parallel:
                build_args.append(f"-j{self.parallel}")

        # TODO: configure verbose
        config.build(build_args=build_args, verbose=1)

        config.install(install_dir)
