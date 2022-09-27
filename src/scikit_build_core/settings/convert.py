from __future__ import annotations

import sys
from pathlib import Path

from .model import CMakeSettings
from .sources import ConfSource, EnvSource, SourceChain, TOMLSource

if sys.version_info >= (3, 11):
    import tomllib
else:
    import tomli as tomllib


def read_cmake_settings(
    pyproject_toml: Path, config_settings: dict[str, str | list[str]]
) -> CMakeSettings:

    with pyproject_toml.open("rb") as f:
        pyproject = tomllib.load(f)

    cmake_section = pyproject.get("tool", {}).get("cmake", {})

    sources = SourceChain(
        EnvSource("CMAKE_"),
        ConfSource("cmake", settings=config_settings),
        TOMLSource(settings=cmake_section),
    )

    return sources.convert_target(CMakeSettings)
