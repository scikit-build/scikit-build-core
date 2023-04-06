from __future__ import annotations

import difflib
import os
import sys
from collections.abc import Generator, Mapping
from pathlib import Path
from typing import Any

from packaging.version import Version

from .. import __version__
from .._compat import tomllib
from .._logging import logger, rich_print
from ..errors import CMakeConfigError
from .skbuild_model import ScikitBuildSettings
from .sources import ConfSource, EnvSource, SourceChain, TOMLSource

__all__ = ["SettingsReader"]


def __dir__() -> list[str]:
    return __all__


class SettingsReader:
    def __init__(
        self,
        pyproject: dict[str, Any],
        config_settings: Mapping[str, str | list[str]],
        *,
        verify_conf: bool = True,
    ) -> None:
        self.sources = SourceChain(
            EnvSource("SKBUILD"),
            ConfSource(settings=config_settings, verify=verify_conf),
            TOMLSource("tool", "scikit-build", settings=pyproject),
            prefixes=["tool", "scikit-build"],
        )
        self.settings = self.sources.convert_target(ScikitBuildSettings)

        if self.settings.minimum_version:
            current_version = Version(__version__)
            minimum_version = Version(self.settings.minimum_version)
            if current_version < minimum_version:
                msg = (
                    f"scikit-build-core version {__version__} is too old. "
                    f"Minimum required version is {self.settings.minimum_version}."
                )
                raise CMakeConfigError(msg)

        if self.settings.editable.mode != "redirect":
            if self.settings.strict_config:
                rich_print("[red][bold]ERROR:[/bold] editable mode must be 'redirect'")
                raise SystemExit(7)
            logger.warning("editable mode must be 'redirect', ignoring")

        if self.settings.editable.rebuild and not self.settings.build_dir:
            rich_print(
                "[red][bold]ERROR:[/bold] editable mode with rebuild requires build_dir"
            )
            raise SystemExit(7)

    def unrecognized_options(self) -> Generator[str, None, None]:
        return self.sources.unrecognized_options(ScikitBuildSettings)

    def suggestions(self, index: int) -> dict[str, list[str]]:
        all_options = list(self.sources[index].all_option_names(ScikitBuildSettings))
        result: dict[str, list[str]] = {
            k: [] for k in self.sources[index].unrecognized_options(ScikitBuildSettings)
        }
        for option in result:
            possibilities = {
                ".".join(k.split(".")[: option.count(".") + 1]) for k in all_options
            }
            result[option] = difflib.get_close_matches(option, possibilities, n=3)

        return result

    def print_suggestions(self) -> None:
        for index in (1, 2):
            name = {1: "config-settings", 2: "pyproject.toml"}[index]
            suggestions_dict = self.suggestions(index)
            if suggestions_dict:
                rich_print(f"[red][bold]ERROR:[/bold] Unrecognized options in {name}:")
                for option, suggestions in suggestions_dict.items():
                    rich_print(f"  [red]{option}", end="")
                    if suggestions:
                        sugstr = ", ".join(suggestions)
                        rich_print(f"[yellow] -> Did you mean: {sugstr}?", end="")
                    rich_print()

    def validate_may_exit(self) -> None:
        unrecognized = list(self.unrecognized_options())
        if unrecognized:
            if self.settings.strict_config:
                sys.stdout.flush()
                self.print_suggestions()
                raise SystemExit(7)
            logger.warning("Unrecognized options: {}", ", ".join(unrecognized))

        for key, value in self.settings.metadata.items():
            if "provider" not in value:
                sys.stdout.flush()
                rich_print(
                    f"[red][bold]ERROR:[/bold] provider= must be provided in {key!r}:"
                )
                raise SystemExit(7)
            if not self.settings.experimental and (
                "provider-path" in value
                or not value["provider"].startswith("scikit_build_core.")
            ):
                sys.stdout.flush()
                rich_print(
                    "[red][bold]ERROR:[/bold] experimental must be enabled currently to use plugins not provided by scikit-build-core"
                )
                raise SystemExit(7)

    @classmethod
    def from_file(
        cls,
        pyproject_path: os.PathLike[str] | str,
        config_settings: Mapping[str, str | list[str]] | None,
        *,
        verify_conf: bool = True,
    ) -> SettingsReader:
        with Path(pyproject_path).open("rb") as f:
            pyproject = tomllib.load(f)

        return cls(pyproject, config_settings or {}, verify_conf=verify_conf)
