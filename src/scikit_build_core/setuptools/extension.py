from __future__ import annotations

import os
import shutil
import sys
import sysconfig
from pathlib import Path

import setuptools
import setuptools.command.build_ext
from packaging.version import Version
from setuptools.dist import Distribution

from .._compat.typing import Literal
from ..builder.builder import Builder
from ..builder.macos import normalize_macos_version
from ..cmake import CMake, CMaker
from ..settings.skbuild_read_settings import SettingsReader

__all__: list[str] = ["CMakeExtension", "cmake_extensions"]


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
        super().__init__(name, [], **kwargs)
        self.sourcedir = Path(sourcedir).resolve()


class CMakeBuild(setuptools.command.build_ext.build_ext):
    def build_extension(self, ext: setuptools.Extension) -> None:
        if not isinstance(ext, CMakeExtension):
            super().build_extension(ext)
            return

        build_tmp_folder = Path(self.build_temp)
        build_temp = build_tmp_folder / "_skbuild"  # TODO: include python platform

        dist = self.distribution  # type: ignore[attr-defined]

        limited_api = dist.get_command_obj("bdist_wheel").py_limited_api
        if limited_api:
            ext.py_limited_api = True

        # This dir doesn't exist, so Path.cwd() is needed for Python < 3.10
        # due to a Windows bug in resolve https://github.com/python/cpython/issues/82852
        ext_fullpath = Path.cwd() / self.get_ext_fullpath(ext.name)  # type: ignore[no-untyped-call]
        extdir = ext_fullpath.parent.resolve()

        # TODO: this is a hack due to moving temporary paths for isolation
        if build_temp.exists():
            shutil.rmtree(build_temp)

        settings = SettingsReader(Path("pyproject.toml"), {}).settings

        cmake = CMake.default_search(
            minimum_version=Version(settings.cmake.minimum_version)
        )

        config = CMaker(
            cmake,
            source_dir=ext.sourcedir,
            build_dir=build_temp,
            build_type=settings.cmake.build_type,
        )

        builder = Builder(
            settings=settings,
            config=config,
        )

        # Setuptools requires this be specified if there's a mismatch.
        if sys.platform.startswith("darwin"):
            arm_only = builder.get_archs() == ["arm64"]
            orig_macos_str = sysconfig.get_platform().rsplit("-", 1)[0].split("-", 1)[1]
            orig_macos = normalize_macos_version(orig_macos_str, arm_only)
            config.env.setdefault("MACOSX_DEPLOYMENT_TARGET", str(orig_macos))

        debug = int(os.environ.get("DEBUG", 0)) if self.debug is None else self.debug
        builder.config.build_type = "Debug" if debug else "Release"

        defines: dict[str, str] = {}

        for key, value in ext.define_macros:
            assert isinstance(value, str), "define_macros values must not be None"
            defines[key] = value

        builder.configure(
            defines=defines,
            name=dist.get_name(),
            version=dist.get_version(),
            limited_abi=ext.py_limited_api,
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


def cmake_extensions(
    dist: Distribution, attr: Literal["cmake_extensions"], value: list[CMakeExtension]
) -> None:
    settings = SettingsReader(Path("pyproject.toml"), {}).settings

    assert attr == "cmake_extensions"
    assert len(value) > 0

    assert (
        not settings.wheel.expand_macos_universal_tags
    ), "wheel.expand_macos_universal_tags is not supported in setuptools mode"
    assert (
        settings.logging.level == "WARNING"
    ), "Logging is not adjustable in setuptools mode yet"
    assert (
        not settings.wheel.py_api
    ), "wheel.py_api is not supported in setuptools mode, use bdist_wheel options instead"

    dist.has_ext_modules = lambda: True  # type: ignore[attr-defined]
    dist.ext_modules = (dist.ext_modules or []) + value

    dist.cmdclass["build_ext"] = CMakeBuild


def cmake_source_dir(
    dist: Distribution, attr: Literal["cmake_source_dir"], value: str
) -> None:
    assert attr == "cmake_source_dir"
    assert Path(value).is_dir()
    assert dist.cmake_extensions is None, "Combining cmake_source_dir= and cmake_extensions= is not allowed"  # type: ignore[attr-defined]
    name = dist.get_name().replace("-", "_")  # type: ignore[attr-defined]

    extensions = [CMakeExtension(name, value)]
    dist.cmake_extensions = extensions  # type: ignore[attr-defined]
    cmake_extensions(dist, "cmake_extensions", extensions)
