from __future__ import annotations

import pathlib
import shutil
import subprocess
import sys
from pathlib import Path

from packaging.version import Version

from ._logging import logger
from ._shutil import Run
from .errors import CMakeAccessError, CMakeConfigError, FailedLiveProcessError

__all__ = ["CMake", "CMakeConfig"]


def __dir__() -> list[str]:
    return __all__


class CMake:
    __slots__ = ("version", "cmake_path")

    # TODO: add option to control search order, etc.
    def __init__(self, *, minimum_version: str | None = None) -> None:
        try:
            import cmake

            self.cmake_path = pathlib.Path(cmake.CMAKE_BIN_DIR) / "cmake"
        except ImportError:
            cmake_path = shutil.which("cmake")
            if cmake_path is not None:
                self.cmake_path = pathlib.Path(cmake_path).resolve()
            else:
                raise RuntimeError(
                    "cmake package missing and cmake command not found on path"
                ) from None

        try:
            result = Run().capture(self.cmake_path, "--version")
        except subprocess.CalledProcessError as err:
            msg = "CMake version undetermined"
            raise CMakeAccessError(err, msg) from None

        self.version = Version(result.stdout.splitlines()[0].split()[-1])
        logger.info("CMake version: {}", self.version)

        if minimum_version is not None and self.version < Version(minimum_version):
            msg = f"CMake version {self.version} is less than minimum version {minimum_version}"
            raise CMakeConfigError(msg)


class CMakeConfig:
    __slots__ = ("cmake", "source_dir", "build_dir")

    def __init__(self, cmake: CMake, *, source_dir: Path, build_dir: Path) -> None:
        self.cmake = cmake
        self.source_dir = source_dir
        self.build_dir = build_dir

        if not self.source_dir.is_dir():
            raise CMakeConfigError(f"source directory {self.source_dir} does not exist")

        self.build_dir.mkdir(parents=True, exist_ok=False)
        if not self.build_dir.is_dir():
            raise CMakeConfigError(
                f"build directory {self.build} must be a (creatable) directory"
            )

    def configure(self) -> None:
        cmake_args = [
            f"-B{self.build_dir}",
            f"-S{self.source_dir}",
        ]

        if not sys.platform.startswith("win32"):
            logger.debug("Selecting Ninja; other generators currently unsupported")
            cmake_args.append("-GNinja")

        try:
            Run().live(self.cmake.cmake_path, *cmake_args)
        except subprocess.CalledProcessError:
            msg = "CMake configuration failed"
            raise FailedLiveProcessError(msg) from None

    def build(self) -> None:
        opts: dict[str, str] = {}
        if sys.platform.startswith("win32"):
            opts["config"] = "Release"

        try:
            Run().live(self.cmake.cmake_path, build=self.build_dir, **opts)
        except subprocess.CalledProcessError:
            msg = "CMake build failed"
            raise FailedLiveProcessError(msg) from None

    def install(self, prefix: Path) -> None:
        try:
            Run().live(
                self.cmake.cmake_path,
                install=self.build_dir,
                prefix=prefix,
            )
        except subprocess.CalledProcessError:
            msg = "CMake install failed"
            raise FailedLiveProcessError(msg) from None
