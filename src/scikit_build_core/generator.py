from __future__ import annotations

import dataclasses
import re
import os
import subprocess
from typing import ClassVar
from collections.abc import Generator, Mapping

from packaging.version import Version

from ._compat.typing import Protocol
from ._logging import logger
from .settings.skbuild_model import NinjaSettings
from .program_search import best_program, get_make_programs, get_ninja_programs
from .errors import NinjaNotFoundError

__all__ = ["CMakeGenerator", "SingleConfigGenerator", "MultiConfigGenerator", "MSVCGenerator", "get_best_generator"]

def __dir__() -> list[str]:
    return __all__


class CMakeGenerator(Protocol):
    name: str
    single_config: ClassVar[bool]
    build_type: str

    def get_env(self) -> dict[str, str]:
        ...

    def get_config_args(self) -> Generator[str, None, None]:
        ...

    def get_build_args(self) -> Generator[str, None, None]:
        ...
    

@dataclasses.dataclass
class SingleConfigGenerator(CMakeGenerator):
    name: str
    single_config: ClassVar[bool] = True
    build_type: str
    prog: str | None

    def get_env(self) -> dict[str, str]:
        env = {"CMAKE_GENERATOR": self.name}
        if self.prog:
            env["CMAKE_MAKE_PROGRAM"] = self.prog
        return env

    def get_config_args(self) -> Generator[str, None, None]:
        if self.build_type:
            yield f"-DCMAKE_BUILD_TYPE={self.build_type}"

    def get_build_args(self) -> Generator[str, None, None]:
        yield from ()


@dataclasses.dataclass
class MultiConfigGenerator(CMakeGenerator):
    name: str
    build_type: str
    single_config: ClassVar[bool] = False

    def get_env(self) -> dict[str, str]:
        return {
            "CMAKE_GENERATOR": self.name,
        }

    def get_config_args(self) -> Generator[str, None, None]:
        yield from ()

    def get_build_args(self) -> Generator[str, None, None]:
        if self.build_type:
            yield f"--config={self.build_type}"


@dataclasses.dataclass
class MSVCGenerator(MultiConfigGenerator):
    platform: str | None

    def get_env(self) -> dict[str, str]:
        env = super().get_env()
        if self.platform:
            env["CMAKE_GENERATOR_PLATFORM"] = self.platform
        return env


def _parse_help_default(txt: str) -> str | None:
    """
    Parses the default generator from the output of cmake --help.
    """

    lines: list[str] = re.findall(
        r"^\*\s*(.*?)(?:\s*\[arch\])?\s*= Generate", txt, re.MULTILINE
    )
    if len(lines) != 1:
        return None

    return lines[0]


def _get_default_generator(cmake: os.PathLike) -> str | None:
        result = subprocess.run(
            [os.fspath(cmake), "--help"],
            check=False,
            capture_output=True,
            encoding="utf-8",
        )
        if result.returncode != 0:
            return None

        return _parse_help_default(result.stdout)


def get_best_generator(cmake: os.PathLike, env: Mapping[str, str], build_type: str, ninja_settings: NinjaSettings | None) -> CMakeGenerator:
    prog = env.get("CMAKE_MAKE_PROGRAM", None)

    if "CMAKE_GENERATOR" in env:
        generator = env["CMAKE_GENERATOR"]
        logger.info("Using CMAKE_GENERATOR {!r}", generator)
    else:
        def_text = _get_default_generator(cmake)
        generator = _parse_help_default(def_text) if def_text else None
        if not generator:
            raise RuntimeError("Failed to parse cmake output for generator!")

        if ninja_settings and generator == "Unix Makefiles" and "CMAKE_MAKE_PROGRAM" not in env:
            ninja = best_program(
                get_ninja_programs(),
                minimum_version=Version(ninja_settings.minimum_version),
            )
            if ninja is not None:
                generator = "Ninja"
                prog = os.fspath(ninja.path)
            if prog is None:
                msg = "Ninja or make is required to build"
                if not ninja_settings.make_fallback:
                    raise NinjaNotFoundError(msg)

                make_programs = list(get_make_programs())
                if not make_programs:
                    raise NinjaNotFoundError(msg)
                prog = os.fspath(make_programs[0])


        logger.info("Using default generator {!r}", generator)

    if "Visual Studio" in generator:
        platform = env.get("CMAKE_GENERATOR_PLATFORM", None)
        return MSVCGenerator(generator, platform=platform, build_type="Release")

    if "XCode" in generator or "Multi-Config" in generator or "MULTI" in generator:
        return MultiConfigGenerator(generator, build_type=build_type)

    return SingleConfigGenerator(generator, prog=prog, build_type=build_type)