from __future__ import annotations

import importlib.metadata
import sys
import typing

if typing.TYPE_CHECKING:
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
    return epg.get(group, [])  # pylint: disable=no-member


def __dir__() -> list[str]:
    return __all__
