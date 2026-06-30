"""
Load configuration contributed by installed packages through the
``scikit-build-core.config.default`` and ``scikit-build-core.config.override``
entry-point groups.

A provider entry point resolves to a callable returning a ``tool.scikit-build``
shaped table (a dict). The group selects the precedence level:

- ``scikit-build-core.config.default``: applied below ``pyproject.toml`` (just
  above the hard-coded defaults).
- ``scikit-build-core.config.override``: applied above ``pyproject.toml`` (but
  below the user's per-build env vars and config-settings).

Within each group the entry-point name is arbitrary; providers are applied in
sorted name order so they compose deterministically.

The returned tables are turned into low/high priority ``TOMLSource``\\ s by
:class:`~scikit_build_core.settings.skbuild_read_settings.SettingsReader`.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from .._compat.importlib import metadata
from .._logging import logger, rich_error

if TYPE_CHECKING:
    from collections.abc import Mapping

__all__ = ["GROUP_DEFAULT", "GROUP_OVERRIDE", "load_config_providers"]


def __dir__() -> list[str]:
    return __all__


GROUP_DEFAULT = "scikit-build-core.config.default"
GROUP_OVERRIDE = "scikit-build-core.config.override"


def _load_group(
    level: str, group: str, *, state: str, env: Mapping[str, str]
) -> list[tuple[str, str, dict[str, object]]]:
    providers: list[tuple[str, str, dict[str, object]]] = []
    for ep in sorted(metadata.entry_points(group=group), key=lambda e: e.name):
        func = ep.load()
        if not callable(func):
            rich_error(f"{group} provider {ep.name!r} must be callable")
        try:
            table = func(state=state, env=env)
        except TypeError:
            table = func()
        if not isinstance(table, dict):
            rich_error(
                f"{group} provider {ep.name!r} must return a tool.scikit-build "
                f"table (dict), got {type(table).__name__}"
            )
        if table:
            logger.debug("Loaded {} entry-point config from {}", level, ep.name)
            providers.append((level, ep.name, table))
    return providers


def load_config_providers(
    *, state: str, env: Mapping[str, str]
) -> list[tuple[str, str, dict[str, object]]]:
    """
    Collect every entry-point provider's table.

    Returns a list of ``(level, name, table)`` tuples. ``override`` providers
    come first, then ``default`` providers; each group is sorted by entry-point
    name so providers compose deterministically (the earlier name wins).
    """
    return [
        *_load_group("override", GROUP_OVERRIDE, state=state, env=env),
        *_load_group("default", GROUP_DEFAULT, state=state, env=env),
    ]
