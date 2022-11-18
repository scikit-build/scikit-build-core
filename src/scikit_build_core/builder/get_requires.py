from __future__ import annotations

import functools
import os
import sys
from collections.abc import Mapping
from pathlib import Path

from packaging.tags import sys_tags
from packaging.version import Version

from .._compat import tomllib
from .._compat.typing import Literal
from ..program_search import (
    best_program,
    get_cmake_programs,
    get_make_programs,
    get_ninja_programs,
)
from ..resources import resources
from ..settings.skbuild_read_settings import SettingsReader

__all__ = ["cmake_ninja_for_build_wheel"]


def __dir__() -> list[str]:
    return __all__


@functools.lru_cache(maxsize=2)
def known_wheels(name: Literal["ninja", "cmake"]) -> frozenset[str]:
    with resources.joinpath("known_wheels.toml").open("rb") as f:
        return frozenset(tomllib.load(f)["tool"]["scikit-build"][name]["known-wheels"])


@functools.lru_cache(maxsize=2)
def is_known_platform(platforms: frozenset[str]) -> bool:
    for tag in sys_tags():
        if tag.platform in platforms:
            return True
    return False


def cmake_ninja_for_build_wheel(
    # pylint: disable-next=unused-argument
    config_settings: Mapping[str, str | list[str]]
    | None = None
) -> list[str]:

    settings = SettingsReader(Path("pyproject.toml"), config_settings or {}).settings

    packages = []
    cmake_min = Version(settings.cmake.minimum_version)
    cmake = best_program(get_cmake_programs(module=False), minimum_version=cmake_min)
    if cmake is None:
        packages.append(f"cmake>={cmake_min}")

    if (
        not sys.platform.startswith("win")
        and os.environ.get("CMAKE_GENERATOR", "Ninja") == "Ninja"
        and not os.environ.get("CMAKE_MAKE_PROGRAM", "")
    ):
        ninja_min = Version(settings.ninja.minimum_version)
        ninja = best_program(
            get_ninja_programs(module=False), minimum_version=ninja_min
        )
        if ninja is None:
            if (
                not settings.ninja.make_fallback
                or is_known_platform(known_wheels("ninja"))
                or not list(get_make_programs())
            ):
                packages.append(f"ninja>={ninja_min}")

    return packages
