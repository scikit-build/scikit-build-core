from __future__ import annotations

import os
import pathlib
import shutil
import subprocess
import sys
from collections.abc import Mapping
from pathlib import Path

from packaging.version import Version

from ._logging import logger
from ._shutil import Run
from .errors import CMakeAccessError, CMakeConfigError, FailedLiveProcessError
from .file_api.query import stateless_query

__all__ = ["CMake", "CMakeConfig", "get_cmake_path"]


def __dir__() -> list[str]:
    return __all__


def get_cmake_path() -> Path:
    """
    Get the path to CMake.
    """
    try:
        import cmake

        return pathlib.Path(cmake.CMAKE_BIN_DIR) / "cmake"
    except ImportError:
        cmake_path = shutil.which("cmake")
        if cmake_path is not None:
            return pathlib.Path(cmake_path).resolve()

        msg = "cmake package missing and cmake command not found on path"
        raise RuntimeError(msg) from None


class CMake:
    __slots__ = ("version", "_cmake_path")

    # TODO: add option to control search order, etc.
    def __init__(self, *, minimum_version: str | None = None) -> None:
        self._cmake_path = get_cmake_path()

        try:
            result = Run().capture(self, "--version")
        except subprocess.CalledProcessError as err:
            msg = "CMake version undetermined"
            raise CMakeAccessError(err, msg) from None

        self.version = Version(result.stdout.splitlines()[0].split()[-1])
        logger.info("CMake version: {}", self.version)

        if minimum_version is not None and self.version < Version(minimum_version):
            msg = f"CMake version {self.version} is less than minimum version {minimum_version}"
            raise CMakeConfigError(msg)

    def __fspath__(self) -> str:
        return os.fspath(self._cmake_path)


class CMakeConfig:
    __slots__ = ("cmake", "source_dir", "build_dir", "init_cache_file")

    def __init__(self, cmake: CMake, *, source_dir: Path, build_dir: Path) -> None:
        self.cmake = cmake
        self.source_dir = source_dir
        self.build_dir = build_dir
        self.init_cache_file = self.build_dir / "CMakeInit.txt"

        if not self.source_dir.is_dir():
            raise CMakeConfigError(f"source directory {self.source_dir} does not exist")

        self.build_dir.mkdir(parents=True, exist_ok=False)
        if not self.build_dir.is_dir():
            raise CMakeConfigError(
                f"build directory {self.build} must be a (creatable) directory"
            )

    def query(self) -> Path:
        return stateless_query(self.build_dir)

    def init_cache(
        self, cache_settings: Mapping[str, str | os.PathLike[str] | bool]
    ) -> None:
        with self.init_cache_file.open("w", encoding="utf-8") as f:
            for key, value in cache_settings.items():
                if isinstance(value, bool):
                    value = "ON" if value else "OFF"
                    f.write(f'set({key} "{value}" CACHE BOOL "")\n')
                elif isinstance(value, os.PathLike):
                    f.write(f'set({key} "{value}" CACHE PATH "")\n')
                else:
                    f.write(f'set({key} "{value}" CACHE STRING "")\n')

    def configure(
        self,
        settings: Mapping[str, str | os.PathLike[str] | bool] | None = None,
        *,
        cmake_args: list[str] | None = None,
    ) -> None:
        settings = settings or {}

        _cmake_args = [
            f"-S{self.source_dir}",
            f"-B{self.build_dir}",
        ]

        if self.init_cache_file.is_file():
            _cmake_args.append(f"-C{self.init_cache_file}")

        if not sys.platform.startswith("win32"):
            logger.debug("Selecting Ninja; other generators currently unsupported")
            _cmake_args.append("-GNinja")

        for key, value in settings.items():
            if isinstance(value, bool):
                value = "ON" if value else "OFF"
                _cmake_args.append(f"-D{key}:BOOL={value}")
            elif isinstance(value, os.PathLike):
                _cmake_args.append(f"-D{key}:PATH={value}")
            else:
                _cmake_args.append(f"-D{key}={value}")

        _cmake_args += cmake_args or []

        try:
            Run().live(self.cmake, *_cmake_args)
        except subprocess.CalledProcessError:
            msg = "CMake configuration failed"
            raise FailedLiveProcessError(msg) from None

    def build(self) -> None:
        opts: dict[str, str] = {}
        if sys.platform.startswith("win32"):
            opts["config"] = "Release"

        try:
            Run().live(self.cmake, build=self.build_dir, **opts)
        except subprocess.CalledProcessError:
            msg = "CMake build failed"
            raise FailedLiveProcessError(msg) from None

    def install(self, prefix: Path) -> None:
        try:
            Run().live(
                self.cmake,
                install=self.build_dir,
                prefix=prefix,
            )
        except subprocess.CalledProcessError:
            msg = "CMake install failed"
            raise FailedLiveProcessError(msg) from None
