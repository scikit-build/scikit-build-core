from __future__ import annotations

import re
import subprocess
import sys
import sysconfig
from collections.abc import Mapping, MutableMapping

from packaging.version import Version

from .._logging import logger
from ..cmake import CMake
from ..errors import NinjaNotFoundError
from ..program_search import best_program, get_make_programs, get_ninja_programs
from ..settings.skbuild_model import NinjaSettings
from .sysconfig import get_cmake_platform

__all__ = ["set_environment_for_gen"]


def __dir__() -> list[str]:
    return __all__


def parse_help_default(txt: str) -> str | None:
    """
    Parses the default generator from the output of cmake --help.
    """

    lines: list[str] = re.findall(
        r"^\*\s*(.*?)(?:\s*\[arch\])?\s*= Generate", txt, re.MULTILINE
    )
    if len(lines) != 1:
        return None

    return lines[0]


def get_default(cmake: CMake) -> str | None:
    """
    Returns the default generator for the current platform. None if it cannot be
    determined.
    """

    result = subprocess.run(
        [str(cmake.cmake_path), "--help"],
        check=False,
        capture_output=True,
        encoding="utf-8",
    )
    if result.returncode != 0:
        return None

    return parse_help_default(result.stdout)


def set_environment_for_gen(
    cmake: CMake, env: MutableMapping[str, str], ninja_settings: NinjaSettings
) -> Mapping[str, str]:
    """
    This function modifies the environment as needed to safely set a generator.

    A reasonable default generator is set if the environment does not already
    have one set; if ninja is present, ninja will be used over make on Unix.
    """

    default = get_default(cmake) or ""
    if default:
        logger.debug("Default generator: {}", default)

    if sysconfig.get_platform().startswith("win") and "Visual Studio" in env.get(
        "CMAKE_GENERATOR", default
    ):
        # This must also be set when *_PLATFORM is set.
        env.setdefault("CMAKE_GENERATOR", default)
        env.setdefault("CMAKE_GENERATOR_PLATFORM", get_cmake_platform(env))
        return {}

    if sys.platform.startswith("win") and not sysconfig.get_platform().startswith(
        "win"
    ):
        # Non-MSVC Windows platforms require Ninja
        default = "Ninja"

    # Try Ninja if it is available, even if make is CMake default
    if default == "Unix Makefiles":
        default = "Ninja"

    if env.get("CMAKE_GENERATOR", default or "Ninja") == "Ninja":
        min_ninja = Version(ninja_settings.minimum_version)
        ninja = best_program(get_ninja_programs(), minimum_version=min_ninja)

        if ninja is not None:
            env.setdefault("CMAKE_GENERATOR", "Ninja")
            logger.debug("CMAKE_GENERATOR: Using ninja: {}", ninja.path)
            return {"CMAKE_MAKE_PROGRAM": str(ninja.path)}

        msg = "Ninja is required to build"
        if not ninja_settings.make_fallback:
            raise NinjaNotFoundError(msg)

        msg = "Ninja or make is required to build"
        make_programs = list(get_make_programs())
        if not make_programs:
            raise NinjaNotFoundError(msg)

        env.setdefault("CMAKE_GENERATOR", "Unix Makefiles")
        logger.debug("CMAKE_GENERATOR: Using make: {}", make_programs[0])
        return {"CMAKE_MAKE_PROGRAM": str(make_programs[0])}

    return {}
