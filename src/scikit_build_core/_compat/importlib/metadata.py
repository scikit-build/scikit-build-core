from __future__ import annotations

__lazy_modules__ = {"typing"}

import importlib.metadata
import sys
import typing

TYPE_CHECKING = False

if TYPE_CHECKING:
    if sys.version_info < (3, 10):
        from importlib.metadata import EntryPoint

        EntryPoints = typing.List[EntryPoint]
    else:
        from importlib.metadata import EntryPoints

__all__ = ["entry_points"]


def entry_points(*, group: str) -> EntryPoints:
    if sys.version_info >= (3, 10):
        return importlib.metadata.entry_points(group=group)

    epg = importlib.metadata.entry_points()
    # On a genuine 3.8/3.9 this is a dict keyed by group. Tests may simulate an
    # old version on a newer runtime, where it is the modern selectable object.
    if hasattr(epg, "select"):
        return epg.select(group=group)
    return epg.get(group, [])  # pylint: disable=no-member


def __dir__() -> list[str]:
    return __all__
