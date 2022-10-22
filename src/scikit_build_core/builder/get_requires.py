from __future__ import annotations

import sys
from collections.abc import Mapping
from pathlib import Path

from packaging.version import Version

from ..program_search import best_program, get_cmake_programs, get_ninja_programs
from ..settings.skbuild_settings import read_settings

__all__ = ["cmake_ninja_for_build_wheel"]


def __dir__() -> list[str]:
    return __all__


def cmake_ninja_for_build_wheel(
    # pylint: disable-next=unused-argument
    config_settings: Mapping[str, str | list[str]]
    | None = None
) -> list[str]:

    settings = read_settings(Path("pyproject.toml"), config_settings or {})

    packages = []
    cmake_min = Version(settings.cmake.minimum_version)
    cmake = best_program(get_cmake_programs(module=False), minimum_version=cmake_min)
    if cmake is None:
        packages.append(f"cmake>={cmake_min}")

    if not sys.platform.startswith("win"):
        ninja_min = Version(settings.ninja.minimum_version)
        ninja = best_program(
            get_ninja_programs(module=False), minimum_version=ninja_min
        )
        if ninja is None:
            packages.append(f"ninja>={ninja_min}")

    return packages
