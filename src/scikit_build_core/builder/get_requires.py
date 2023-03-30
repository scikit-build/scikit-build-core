from __future__ import annotations

import dataclasses
import functools
import importlib
import os
import sys
from collections.abc import Generator, Mapping

from packaging.tags import sys_tags
from packaging.version import Version

from .._compat import tomllib
from .._compat.typing import Literal
from .._logging import logger
from ..program_search import (
    best_program,
    get_cmake_programs,
    get_make_programs,
    get_ninja_programs,
)
from ..resources import resources
from ..settings.skbuild_read_settings import SettingsReader

__all__ = ["GetRequires"]


def __dir__() -> list[str]:
    return __all__


@functools.lru_cache(maxsize=2)
def known_wheels(name: Literal["ninja", "cmake"]) -> frozenset[str]:
    with resources.joinpath("known_wheels.toml").open("rb") as f:
        return frozenset(tomllib.load(f)["tool"]["scikit-build"][name]["known-wheels"])


@functools.lru_cache(maxsize=2)
def is_known_platform(platforms: frozenset[str]) -> bool:
    return any(tag.platform in platforms for tag in sys_tags())


def _load_get_requires_hook(
    mod_name: str,
    config_settings: Mapping[str, list[str] | str] | None = None,
) -> list[str]:
    module = importlib.import_module(mod_name)
    hook = getattr(module, "get_requires_for_dynamic_metadata", None)
    return [] if hook is None else hook(config_settings)  # type: ignore[no-any-return]


@dataclasses.dataclass
class GetRequires:
    config_settings: Mapping[str, list[str] | str] | None = None

    def __post_init__(self) -> None:
        self._settings = SettingsReader.from_file(
            "pyproject.toml", self.config_settings
        ).settings

    def cmake(self) -> Generator[str, None, None]:
        cmake_min = Version(self._settings.cmake.minimum_version)
        cmake = best_program(
            get_cmake_programs(module=False), minimum_version=cmake_min
        )
        if cmake is None:
            yield f"cmake>={cmake_min}"
            return
        logger.debug("Found system CMake: {} - not requiring PyPI package", cmake)

    def ninja(self) -> Generator[str, None, None]:
        # On Windows, Ninja is not default
        if sys.platform.startswith("win") and "Ninja" not in os.environ.get(
            "CMAKE_GENERATOR", ""
        ):
            return

        # If something besides Windows is set, don't add ninja
        if "Ninja" not in os.environ.get("CMAKE_GENERATOR", "Ninja"):
            return

        # If CMAKE_MAKE_PROGRAM is set, don't add anything, someone already knows what they want
        if os.environ.get("CMAKE_MAKE_PROGRAM", ""):
            return

        ninja_min = Version(self._settings.ninja.minimum_version)
        ninja = best_program(
            get_ninja_programs(module=False), minimum_version=ninja_min
        )
        if ninja is not None:
            logger.debug("Found system Ninja: {} - not requiring PyPI package", ninja)
            return

        if (
            self._settings.ninja.make_fallback
            and not is_known_platform(known_wheels("ninja"))
            and list(get_make_programs())
        ):
            logger.debug(
                "Found system Make & not on known platform - not requiring PyPI package for Ninja"
            )
            return
        yield f"ninja>={ninja_min}"

    def dynamic_metadata(self) -> Generator[str, None, None]:
        for plugins in self._settings.metadata.values():
            yield from _load_get_requires_hook(plugins, self.config_settings)
