from __future__ import annotations

import functools
import importlib.metadata
import sys

TYPE_CHECKING = False

if TYPE_CHECKING:
    if sys.version_info < (3, 10):
        from importlib.metadata import EntryPoint

        EntryPoints = list[EntryPoint]
    else:
        from importlib.metadata import EntryPoints

__all__ = ["cached_entry_points", "entry_points"]


def entry_points(*, group: str) -> EntryPoints:
    if sys.version_info >= (3, 10):
        return importlib.metadata.entry_points(group=group)

    epg = importlib.metadata.entry_points()
    return epg.get(group, [])  # pylint: disable=no-member


@functools.cache
def cached_entry_points(*, group: str) -> EntryPoints:
    """Like ``entry_points``, but scans the installed distributions only once.

    ``entry_points`` is read from the module global, so a monkeypatch of it is
    seen. Call ``cached_entry_points.cache_clear()`` if the entry points change.
    """
    return entry_points(group=group)


def __dir__() -> list[str]:
    return __all__
