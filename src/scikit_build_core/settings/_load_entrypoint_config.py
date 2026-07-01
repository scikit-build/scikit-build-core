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

__lazy_modules__ = {
    f"{(__spec__.parent or '').rsplit('.', 1)[0]}._compat",
    f"{(__spec__.parent or '').rsplit('.', 1)[0]}._logging",
    "inspect",
}

import inspect

from .._compat.importlib import metadata
from .._logging import logger, rich_error, rich_warning

__all__ = ["GROUP_DEFAULT", "GROUP_OVERRIDE", "load_config_providers"]


def __dir__() -> list[str]:
    return __all__


TYPE_CHECKING = False
if TYPE_CHECKING:
    from collections.abc import Callable, Mapping
    from importlib.metadata import EntryPoint


GROUP_DEFAULT = "scikit-build-core.config.default"
GROUP_OVERRIDE = "scikit-build-core.config.override"


def _dist_name(ep: object) -> str:
    """Best-effort distribution name for an entry point (for diagnostics)."""
    dist = getattr(ep, "dist", None)
    return getattr(dist, "name", None) or "unknown distribution"


def _call_provider(
    func: Callable[..., object], *, state: str, env: Mapping[str, str]
) -> object:
    """Call a provider with exactly the ``state``/``env`` arguments it accepts.

    The documented contract is per-argument: ``state`` and ``env`` are each
    passed only when the callable accepts them (a ``**kwargs`` provider accepts
    both). The callable is invoked exactly once, so an argument-binding retry
    can never re-run a provider's side effects or swallow a body ``TypeError``.
    """
    params = inspect.signature(func).parameters
    accepts_var_kw = any(
        p.kind is inspect.Parameter.VAR_KEYWORD for p in params.values()
    )
    kwargs: dict[str, object] = {}
    if accepts_var_kw or "state" in params:
        kwargs["state"] = state
    if accepts_var_kw or "env" in params:
        kwargs["env"] = env
    return func(**kwargs)


def _load_group(
    level: str, group: str, *, state: str, env: Mapping[str, str]
) -> list[tuple[str, str, dict[str, object]]]:
    providers: list[tuple[str, str, dict[str, object]]] = []
    by_name: dict[str, list[EntryPoint]] = {}
    for ep in metadata.entry_points(group=group):
        by_name.setdefault(ep.name, []).append(ep)
    for name in sorted(by_name):
        eps = by_name[name]
        if len(eps) > 1:
            dists = ", ".join(_dist_name(e) for e in eps)
            rich_warning(
                f"Multiple {group!r} providers named {name!r} found "
                f"(from {dists}); using the first"
            )
        ep = eps[0]
        func = ep.load()
        if not callable(func):
            rich_error(f"{group} provider {ep.name!r} must be callable")
        table = _call_provider(func, state=state, env=env)
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
