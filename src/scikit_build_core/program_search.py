from __future__ import annotations

import contextlib
import shutil
import subprocess
from collections.abc import Generator, Iterable
from pathlib import Path
from typing import NamedTuple

from packaging.version import InvalidVersion, Version

from ._logging import logger
from ._shutil import Run

__all__ = ["get_cmake_programs", "get_ninja_programs", "best_program", "Program"]


def __dir__() -> list[str]:
    return __all__


class Program(NamedTuple):
    path: Path
    version: Version | None


def _get_cmake_path(*, module: bool = True) -> Generator[Path, None, None]:
    """
    Get the path to CMake.
    """
    if module:
        with contextlib.suppress(ImportError):
            # If a "cmake" directory exists, this will also ImportError
            from cmake import CMAKE_BIN_DIR

            yield Path(CMAKE_BIN_DIR) / "cmake"

    candidates = ("cmake3", "cmake")
    for candidate in candidates:
        cmake_path = shutil.which(candidate)
        if cmake_path is not None:
            yield Path(cmake_path)


def _get_ninja_path(*, module: bool = True) -> Generator[Path, None, None]:
    """
    Get the path to ninja.
    """

    if module:
        with contextlib.suppress(ImportError):
            from ninja import BIN_DIR

            yield Path(BIN_DIR) / "ninja"

    # Matches https://gitlab.kitware.com/cmake/cmake/-/blob/master/Modules/CMakeNinjaFindMake.cmake
    candidates = ("ninja-build", "ninja", "samu")
    for candidate in candidates:
        ninja_path = shutil.which(candidate)
        if ninja_path is not None:
            yield Path(ninja_path)


def get_cmake_programs(*, module: bool = True) -> Generator[Program, None, None]:
    """
    Get the path and version for CMake. If the version cannot be determined,
    yiels (path, None). Otherwise, yields (path, version). Best matches are
    yielded first.
    """
    for cmake_path in _get_cmake_path(module=module):
        try:
            result = Run().capture(cmake_path, "--version")
        except subprocess.CalledProcessError:
            yield Program(cmake_path, None)
            continue

        try:
            version = Version(result.stdout.splitlines()[0].split()[-1])
        except (IndexError, InvalidVersion):
            logger.warning(f"Could not determine CMake version, got {result.stdout!r}")
            yield Program(cmake_path, None)
            continue

        logger.info("CMake version: {}", version)
        yield Program(cmake_path, version)


def get_ninja_programs(*, module: bool = True) -> Generator[Program, None, None]:
    """
    Get the path and version for Ninja. If the version cannot be determined,
    yields (path, None). Otherwise, yields (path, version). Best matches are
    yielded first.
    """
    for ninja_path in _get_ninja_path(module=module):
        try:
            result = Run().capture(ninja_path, "--version")
        except subprocess.CalledProcessError:
            yield Program(ninja_path, None)
            continue

        try:
            version = Version(".".join(result.stdout.strip().split(".")[:3]))
        except ValueError:
            yield Program(ninja_path, None)
            continue

        logger.info("Ninja version: {}", version)
        yield Program(ninja_path, version)


def get_make_programs() -> Generator[Path, None, None]:
    """
    Get the path to make.
    """
    candidates = ("gmake", "make")
    for candidate in candidates:
        make_path = shutil.which(candidate)
        if make_path is not None:
            yield Path(make_path)


def best_program(
    programs: Iterable[Program], *, minimum_version: Version | None
) -> Program | None:
    """
    Select the first program entry that is of a supported version, or None if not found.
    """

    for program in programs:
        if minimum_version is None:
            return program
        if program.version is not None and program.version >= minimum_version:
            return program

    return None
