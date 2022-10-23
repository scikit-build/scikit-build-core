from __future__ import annotations

import os
import shutil
from pathlib import Path

import setuptools
import setuptools.command.build_ext
from packaging.version import Version

from ..builder.builder import Builder
from ..cmake import CMake, CMakeConfig
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

        build_tmp_folder = Path(self.build_temp)
        build_temp = build_tmp_folder / "_skbuild"  # TODO: include python platform

        # This dir doesn't exist, so Path.cwd() is needed for Python < 3.10
        # due to a Windows bug in resolve https://github.com/python/cpython/issues/82852
        ext_fullpath = Path.cwd() / self.get_ext_fullpath(ext.name)  # type: ignore[no-untyped-call]
        extdir = ext_fullpath.parent.resolve()

        # TODO: this is a hack due to moving temporary paths for isolation
        if build_temp.exists():
            shutil.rmtree(build_temp)

        settings = read_settings(Path("pyproject.toml"), {})

        cmake = CMake.default_search(
            minimum_version=Version(settings.cmake.minimum_version)
        )

        config = CMakeConfig(
            cmake,
            source_dir=ext.sourcedir,
            build_dir=build_temp,
        )

        builder = Builder(
            settings=settings,
            config=config,
        )

        debug = int(os.environ.get("DEBUG", 0)) if self.debug is None else self.debug
        builder.config.build_type = "Debug" if debug else "Release"

        defines: dict[str, str] = {}

        for key, value in ext.define_macros:
            assert isinstance(value, str), "define_macros values must not be None"
            defines[key] = value

        dist = self.distribution  # type: ignore[attr-defined]
        builder.configure(
            defines=defines,
            name=dist.get_name(),
            version=dist.get_version(),
        )

        # Set CMAKE_BUILD_PARALLEL_LEVEL to control the parallel build level
        # across all generators.
        build_args = []
        if "CMAKE_BUILD_PARALLEL_LEVEL" not in builder.config.env:
            # self.parallel is a Python 3 only way to set parallel jobs by hand
            # using -j in the build_ext call, not supported by pip or PyPA-build.
            if hasattr(self, "parallel") and self.parallel:
                build_args.append(f"-j{self.parallel}")

        builder.build(build_args=build_args)
        builder.install(extdir)
