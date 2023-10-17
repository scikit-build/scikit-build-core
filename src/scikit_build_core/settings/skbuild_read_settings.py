from __future__ import annotations

import copy
import difflib
import platform
import re
import sys
from pathlib import Path
from typing import TYPE_CHECKING, Any

from packaging.specifiers import SpecifierSet
from packaging.version import Version

from .. import __version__
from .._compat import tomllib
from .._logging import logger, rich_print
from ..errors import CMakeConfigError
from .skbuild_model import ScikitBuildSettings
from .sources import ConfSource, EnvSource, SourceChain, TOMLSource

if TYPE_CHECKING:
    import os
    from collections.abc import Generator, Mapping

__all__ = ["SettingsReader"]


def __dir__() -> list[str]:
    return __all__


def version_match(value: str, match: str, name: str) -> str:
    """
    Returns a non-empty string if a version matches a specifier.
    """
    matcher = SpecifierSet(match)
    did_match = matcher.contains(value)
    return f"{match!r} matched {name} {value}" if did_match else ""


def regex_match(value: str, match: str) -> str:
    """
    Returns a non-empty string if a value matches a regex.
    """
    did_match = re.compile(match).search(value) is not None
    return f"{match!r} matched {value}" if did_match else ""


def override_match(
    python_version: str | None = None,
    implementation_name: str | None = None,
    implementation_version: str | None = None,
    platform_system: str | None = None,
    platform_machine: str | None = None,
    platform_node: str | None = None,
) -> bool:
    matches = []

    if python_version is not None:
        current_python_version = ".".join(str(x) for x in sys.version_info[:2])
        match_msg = version_match(current_python_version, python_version, "Python")
        matches.append(match_msg)

    if implementation_name is not None:
        current_impementation_name = sys.implementation.name
        match_msg = regex_match(current_impementation_name, implementation_name)
        matches.append(match_msg)

    if implementation_version is not None:
        info = sys.implementation.version
        version = f"{info.major}.{info.minor}.{info.micro}"
        kind = info.releaselevel
        if kind != "final":
            version += f"{kind[0]}{info.serial}"
        match_msg = version_match(
            version, implementation_version, "Python implementation"
        )
        matches.append(match_msg)

    if platform_system is not None:
        current_platform_system = sys.platform
        match_msg = regex_match(current_platform_system, platform_system)
        matches.append(match_msg)

    if platform_machine is not None:
        current_platform_machine = platform.machine()
        match_msg = regex_match(current_platform_machine, platform_machine)
        matches.append(match_msg)

    if platform_node is not None:
        current_platform_node = platform.node()
        match_msg = regex_match(current_platform_node, platform_node)
        matches.append(match_msg)

    if not matches:
        msg = "At least one override must be provided"
        raise ValueError(msg)

    matched = all(matches)
    if matched:
        logger.info("Overrides {}", " and ".join(matches))
    return matched


class SettingsReader:
    def __init__(
        self,
        pyproject: dict[str, Any],
        config_settings: Mapping[str, str | list[str]],
        *,
        verify_conf: bool = True,
    ) -> None:
        pyproject = copy.deepcopy(pyproject)

        # Process overrides into the main dictionary if they match
        tool_skb = pyproject.get("tool", {}).get("scikit-build", {})
        for override in tool_skb.pop("overrides", []):
            select = {k.replace("-", "_"): v for k, v in override.pop("if").items()}
            if override_match(**select):
                for key, value in override.items():
                    if isinstance(value, dict):
                        for key2, value2 in value.items():
                            inner = tool_skb.get(key, {})
                            inner[key2] = value2
                            tool_skb[key] = inner
                    else:
                        tool_skb[key] = value

        self.sources = SourceChain(
            EnvSource("SKBUILD"),
            ConfSource(settings=config_settings, verify=verify_conf),
            TOMLSource("tool", "scikit-build", settings=pyproject),
            prefixes=["tool", "scikit-build"],
        )
        self.settings = self.sources.convert_target(ScikitBuildSettings)

        if self.settings.minimum_version:
            current_version = Version(__version__)
            minimum_version = self.settings.minimum_version
            if current_version < minimum_version:
                msg = (
                    f"scikit-build-core version {__version__} is too old. "
                    f"Minimum required version is {self.settings.minimum_version}."
                )
                raise CMakeConfigError(msg)

        if self.settings.editable.rebuild and not self.settings.build_dir:
            rich_print(
                "[red][bold]ERROR:[/bold] editable mode with rebuild requires build_dir"
            )
            raise SystemExit(7)

        install_policy = (
            self.settings.minimum_version is None
            or self.settings.minimum_version >= Version("0.5")
        )
        if self.settings.install.strip is None:
            self.settings.install.strip = install_policy

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

        for gen in self.settings.generate:
            if not gen.template and not gen.template_path:
                sys.stdout.flush()
                rich_print(
                    "[red][bold]ERROR:[/bold] template= or template-path= must be provided in generate"
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
