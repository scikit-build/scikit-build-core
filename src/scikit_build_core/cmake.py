from __future__ import annotations

import contextlib
import dataclasses
import os
import pathlib
import shutil
import subprocess
import sys
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Generator, TypeVar

from packaging.version import Version

from ._logging import logger
from ._shutil import Run
from .errors import (
    CMakeAccessError,
    CMakeConfigError,
    CMakeNotFoundError,
    FailedLiveProcessError,
)

__all__ = ["CMake", "CMakeConfig", "get_cmake_path"]


def __dir__() -> list[str]:
    return __all__


def get_cmake_path(*, module: bool = True) -> Path:
    """
    Get the path to CMake.
    """
    if module:
        with contextlib.suppress(ImportError):
            import cmake

            return pathlib.Path(cmake.CMAKE_BIN_DIR) / "cmake"

    cmake_path = shutil.which("cmake")
    if cmake_path is not None:
        return pathlib.Path(cmake_path).resolve()

    msg = "cmake package missing and cmake command not found on path"
    raise CMakeNotFoundError(msg) from None


Self = TypeVar("Self", bound="CMake")


@dataclasses.dataclass(frozen=True)
class CMake:
    version: Version
    cmake_path: Path

    # TODO: add option to control search order, etc.
    @classmethod
    def default_search(
        cls: type[Self], *, minimum_version: str | None = None, module: bool = True
    ) -> Self:
        cmake_path = get_cmake_path(module=module)

        try:
            result = Run().capture(cmake_path, "--version")
        except subprocess.CalledProcessError as err:
            msg = "CMake version undetermined"
            raise CMakeAccessError(err, msg) from None

        version = Version(result.stdout.splitlines()[0].split()[-1])
        logger.info("CMake version: {}", version)

        if minimum_version is not None and version < Version(minimum_version):
            msg = f"CMake version {version} is less than minimum version {minimum_version}"
            raise CMakeConfigError(msg)

        return cls(version=version, cmake_path=cmake_path)

    def __fspath__(self) -> str:
        return os.fspath(self.cmake_path)


@dataclasses.dataclass
class CMakeConfig:
    cmake: CMake
    source_dir: Path
    build_dir: Path
    init_cache_file: Path = dataclasses.field(init=False, default=Path())
    module_dirs: list[Path] = dataclasses.field(default_factory=list)
    env: dict[str, str] = dataclasses.field(init=False, default_factory=os.environ.copy)

    def __post_init__(self) -> None:
        self.init_cache_file = self.build_dir / "CMakeInit.txt"

        if not self.source_dir.is_dir():
            raise CMakeConfigError(f"source directory {self.source_dir} does not exist")

        self.build_dir.mkdir(parents=True, exist_ok=True)
        if not self.build_dir.is_dir():
            raise CMakeConfigError(
                f"build directory {self.build} must be a (creatable) directory"
            )

    def init_cache(
        self, cache_settings: Mapping[str, str | os.PathLike[str] | bool]
    ) -> None:
        with self.init_cache_file.open("w", encoding="utf-8") as f:
            for key, value in cache_settings.items():
                if isinstance(value, bool):
                    value = "ON" if value else "OFF"
                    f.write(f'set({key} {value} CACHE BOOL "")\n')
                elif isinstance(value, os.PathLike):
                    f.write(f'set({key} [===[{value}]===] CACHE PATH "")\n')
                else:
                    f.write(f'set({key} [===[{value}]===] CACHE STRING "")\n')
        logger.debug(
            "{}:\n{}",
            self.init_cache_file,
            self.init_cache_file.read_text(encoding="utf-8"),
        )

    def _compute_cmake_args(
        self, settings: Mapping[str, str | os.PathLike[str] | bool]
    ) -> Generator[str, None, None]:
        yield f"-S{self.source_dir}"
        yield f"-B{self.build_dir}"

        if self.init_cache_file.is_file():
            yield f"-C{self.init_cache_file}"

        if not sys.platform.startswith("win32"):
            logger.debug("Selecting Ninja; other generators currently unsupported")
            yield "-GNinja"

        for key, value in settings.items():
            if isinstance(value, bool):
                value = "ON" if value else "OFF"
                yield f"-D{key}:BOOL={value}"
            elif isinstance(value, os.PathLike):
                yield f"-D{key}:PATH={value}"
            else:
                yield f"-D{key}={value}"

        if self.module_dirs:
            module_dirs_str = ";".join(map(str, self.module_dirs))
            yield f"-DCMAKE_MODULE_PATH={module_dirs_str}"

    def configure(
        self,
        *,
        defines: Mapping[str, str | os.PathLike[str] | bool] | None = None,
        cmake_args: Sequence[str] = (),
    ) -> None:
        _cmake_args = self._compute_cmake_args(defines or {})

        try:
            Run(env=self.env).live(self.cmake, *_cmake_args, *cmake_args)
        except subprocess.CalledProcessError:
            msg = "CMake configuration failed"
            raise FailedLiveProcessError(msg) from None

    def build(self, build_args: Sequence[str] = (), *, verbose: int = 0) -> None:
        local_args = ["-v"] * verbose
        if sys.platform.startswith("win32"):
            local_args += ["--config", "Release"]

        try:
            Run(env=self.env).live(
                self.cmake, "--build", self.build_dir, *build_args, *local_args
            )
        except subprocess.CalledProcessError:
            msg = "CMake build failed"
            raise FailedLiveProcessError(msg) from None

    def install(self, prefix: Path) -> None:
        try:
            Run(env=self.env).live(
                self.cmake,
                "--install",
                self.build_dir,
                "--prefix",
                prefix,
            )
        except subprocess.CalledProcessError:
            msg = "CMake install failed"
            raise FailedLiveProcessError(msg) from None
