from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path

from .._compat import tomllib
from .cmake_model import ScikitBuildSettings
from .sources import ConfSource, EnvSource, SourceChain, TOMLSource

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
