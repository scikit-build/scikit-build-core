"""
Load configuration contributed by installed packages through the
``scikit-build-core.config`` entry-point group.

A provider entry point resolves to a callable returning a ``tool.scikit-build``
shaped table (a dict). The first dotted segment of the entry-point *name*
selects the precedence level:

- ``default``: applied below ``pyproject.toml`` (just above hard-coded defaults).
- ``override``: applied above ``pyproject.toml`` (but below the user's per-build
  env vars and config-settings).

The returned tables are turned into low/high priority ``TOMLSource``\\ s by
:class:`~scikit_build_core.settings.skbuild_read_settings.SettingsReader`.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from .._compat.importlib import metadata
from .._logging import logger, rich_error, rich_warning

if TYPE_CHECKING:
    from collections.abc import Mapping

__all__ = ["GROUP", "load_config_providers"]


def __dir__() -> list[str]:
    return __all__


GROUP = "scikit-build-core.config"
_LEVELS = frozenset({"default", "override"})


def load_config_providers(
    *, state: str, env: Mapping[str, str]
) -> list[tuple[str, str, dict[str, object]]]:
    """
    Collect every ``scikit-build-core.config`` provider's table.

    Returns a list of ``(level, name, table)`` tuples, sorted by entry-point
    name so multiple providers compose deterministically. ``level`` is always
    ``"default"`` or ``"override"``; providers with any other name are skipped
    with a warning.
    """
    providers: list[tuple[str, str, dict[str, object]]] = []
    for ep in sorted(metadata.entry_points(group=GROUP), key=lambda e: e.name):
        level = ep.name.split(".", 1)[0]
        if level not in _LEVELS:
            rich_warning(
                f"Ignoring {GROUP} provider {ep.name!r}: the name must start with "
                "'default' or 'override' to select the precedence level"
            )
            continue
        func = ep.load()
        if not callable(func):
            rich_error(f"{GROUP} provider {ep.name!r} must be callable")
        try:
            table = func(state=state, env=env)
        except TypeError:
            table = func()
        if not isinstance(table, dict):
            rich_error(
                f"{GROUP} provider {ep.name!r} must return a tool.scikit-build "
                f"table (dict), got {type(table).__name__}"
            )
        if table:
            logger.debug("Loaded {} entry-point config from {}", level, ep.name)
            providers.append((level, ep.name, table))
    return providers
