from __future__ import annotations

import sys
from collections.abc import MutableMapping

from packaging.version import Version

from .._logging import logger
from ..cmake import CMaker
from ..errors import NinjaNotFoundError
from ..program_search import best_program, get_make_programs, get_ninja_programs
from ..settings.skbuild_model import NinjaSettings
from .sysconfig import get_cmake_platform

__all__ = ["set_environment_for_gen"]


def __dir__() -> list[str]:
    return __all__


def set_environment_for_gen(
    cmaker: CMaker, ninja_settings: NinjaSettings
) -> None:
    """
    This function modifies the environment as needed to safely set a generator.

    A reasonable default generator is set if the environment does not already
    have one set; if ninja is present, ninja will be used over make on Unix.
    """

    default = cmaker.generator or ""
    if default:
        logger.debug("Default generator: {}", default)

    if sys.platform.startswith("win32"):
        if "Visual Studio" in cmaker.env.get("CMAKE_GENERATOR", default):
            # This must also be set when *_PLATFORM is set.
            cmaker.env.setdefault("CMAKE_GENERATOR", default)
            cmaker.env.setdefault("CMAKE_GENERATOR_PLATFORM", get_cmake_platform(cmaker.env))
    elif cmaker.env.get("CMAKE_GENERATOR", "Ninja") == "Ninja" and not cmaker.env.get(
        "CMAKE_MAKE_PROGRAM", ""
    ):
        ninja = best_program(
            get_ninja_programs(),
            minimum_version=Version(ninja_settings.minimum_version),
        )
        if ninja is None:
            msg = "Ninja or make is required to build"
            if not ninja_settings.make_fallback:
                raise NinjaNotFoundError(msg)

            make_programs = list(get_make_programs())
            if not make_programs:
                raise NinjaNotFoundError(msg)
            cmaker.env.setdefault("CMAKE_GENERATOR", "Unix Makefiles")
            cmaker.env.setdefault("CMAKE_MAKE_PROGRAM", str(make_programs[0]))
            logger.debug("CMAKE_GENERATOR: Using make: {}", make_programs[0])
        else:
            cmaker.env.setdefault("CMAKE_GENERATOR", "Ninja")
            cmaker.env.setdefault("CMAKE_MAKE_PROGRAM", str(ninja.path))
            logger.debug("CMAKE_GENERATOR: Using ninja: {}", ninja.path)
