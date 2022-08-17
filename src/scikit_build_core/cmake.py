from __future__ import annotations

import pathlib
import shutil
import subprocess
from pathlib import Path

from packaging.version import Version

from .errors import CMakeAccessError, CMakeConfigError, FailedLiveProcessError
from .logging import logger

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
                )

        logger.debug("RUN: {} --version", self.cmake_path)

        try:
            result = subprocess.run(
                [self.cmake_path, "--version"],
                capture_output=True,
                text=True,
                check=True,
            )
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
        logger.debug(
            "Selecting ninja generator; support for other generators may be added in the future"
        )

        cmake_args = [
            "-GNinja",
            f"-B{self.build_dir}",
            f"-S{self.source_dir}",
        ]
        logger.debug("RUN: {} {}", self.cmake.cmake_path, " ".join(cmake_args))

        try:
            subprocess.run(
                [str(self.cmake.cmake_path), *cmake_args],
                capture_output=False,
                check=True,
            )
        except subprocess.CalledProcessError:
            msg = "CMake configuration failed"
            raise FailedLiveProcessError(msg) from None

    def build(self) -> None:
        logger.debug("RUN: {} {}", self.cmake.cmake_path, f"--build {self.build_dir}")

        try:
            subprocess.run(
                [self.cmake.cmake_path, "--build", self.build_dir],
                capture_output=False,
                check=True,
            )
        except subprocess.CalledProcessError:
            msg = "CMake build failed"
            raise FailedLiveProcessError(msg) from None

    def install(self, prefix: Path) -> None:
        logger.debug(
            "RUN: {} --install {} --prefix {}",
            self.cmake.cmake_path,
            self.build_dir,
            prefix,
        )

        try:
            subprocess.run(
                [
                    self.cmake.cmake_path,
                    "--install",
                    self.build_dir,
                    "--prefix",
                    prefix,
                ],
                capture_output=False,
                check=True,
            )
        except subprocess.CalledProcessError:
            msg = "CMake install failed"
            raise FailedLiveProcessError(msg) from None
