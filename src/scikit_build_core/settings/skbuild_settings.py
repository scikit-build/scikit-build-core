from __future__ import annotations

import sys
from collections.abc import Mapping
from pathlib import Path

from .cmake_model import ScikitBuildSettings
from .sources import ConfSource, EnvSource, SourceChain, TOMLSource

if sys.version_info >= (3, 11):
    import tomllib
else:
    import tomli as tomllib


__all__ = ["read_settings"]


def __dir__() -> list[str]:
    return __all__


def read_settings(
    pyproject_toml: Path, config_settings: Mapping[str, str | list[str]]
) -> ScikitBuildSettings:

    with pyproject_toml.open("rb") as f:
        pyproject = tomllib.load(f)

    cmake_section = pyproject.get("tool", {}).get("scikit-build", {})

    sources = SourceChain(
        EnvSource("SKBUILD"),
        ConfSource("scikit-build", settings=config_settings),
        TOMLSource(settings=cmake_section),
    )

    return sources.convert_target(ScikitBuildSettings)
