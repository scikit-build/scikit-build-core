from __future__ import annotations

import sys
import typing

if sys.version_info < (3, 8):
    import importlib_metadata as _metadata
    from importlib_metadata import PathDistribution, version
else:
    import importlib.metadata as _metadata
    from importlib.metadata import PathDistribution, version


if typing.TYPE_CHECKING:
    if sys.version_info < (3, 8):
        from importlib_metadata import EntryPoints
    elif sys.version_info < (3, 10):
        from importlib.metadata import EntryPoint

        EntryPoints = typing.List[EntryPoint]
    else:
        from importlib.metadata import EntryPoints

__all__ = ["entry_points", "PathDistribution", "version"]


def entry_points(*, group: str) -> EntryPoints:
    if sys.version_info >= (3, 10):
        return _metadata.entry_points(group=group)

    epg = _metadata.entry_points()

    if sys.version_info < (3, 8) and hasattr(epg, "select"):
        return epg.select(group=group)  # type: ignore[no-any-return, no-untyped-call]

    return epg.get(group, [])


def __dir__() -> list[str]:
    return __all__
