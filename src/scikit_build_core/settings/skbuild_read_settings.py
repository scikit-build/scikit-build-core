from __future__ import annotations

import sys
from collections.abc import Generator, Mapping
from pathlib import Path

from .._compat import tomllib
from .._logging import logger
from .skbuild_model import ScikitBuildSettings
from .sources import ConfSource, EnvSource, SourceChain, TOMLSource

__all__ = ["SettingsReader"]


def __dir__() -> list[str]:
    return __all__


class SettingsReader:
    def __init__(
        self,
        pyproject_toml: Path,
        config_settings: Mapping[str, str | list[str]],
        verify_conf: bool = True,
    ) -> None:
        with pyproject_toml.open("rb") as f:
            pyproject = tomllib.load(f)

        cmake_section = pyproject.get("tool", {}).get("scikit-build", {})

        self.sources = SourceChain(
            EnvSource("SKBUILD"),
            ConfSource("scikit-build", settings=config_settings, verify=verify_conf),
            TOMLSource(settings=cmake_section),
        )
        self.settings = self.sources.convert_target(ScikitBuildSettings)

    def unrecognized_options(self) -> Generator[str, None, None]:
        return self.sources.unrecognized_options(ScikitBuildSettings)

    def validate_may_exit(self) -> None:
        unrecognized = list(self.unrecognized_options())
        if unrecognized:
            if self.settings.strict_config:
                sys.stdout.flush()
                logger.error("Unrecognized options:\n\n  {}", "\n  ".join(unrecognized))
                raise SystemExit(7)
            logger.warning("Unrecognized options: {}", ", ".join(unrecognized))
