from __future__ import annotations

import sys
from collections.abc import Mapping
from pathlib import Path

from .cmake_model import CMakeSettings
from .sources import ConfSource, EnvSource, SourceChain, TOMLSource

if sys.version_info >= (3, 11):
    import tomllib
else:
    import tomli as tomllib


__all__ = ["read_cmake_settings"]


def __dir__() -> list[str]:
    return __all__


def read_cmake_settings(
    pyproject_toml: Path, config_settings: Mapping[str, str | list[str]]
) -> CMakeSettings:

    with pyproject_toml.open("rb") as f:
        pyproject = tomllib.load(f)

    cmake_section = pyproject.get("tool", {}).get("cmake", {})

    sources = SourceChain(
        EnvSource("SKBUILD"),
        ConfSource("cmake", settings=config_settings),
        TOMLSource(settings=cmake_section),
    )

    return sources.convert_target(CMakeSettings)
