from __future__ import annotations

import sys

if sys.version_info < (3, 8):
    import importlib_metadata as _metadata
else:
    import importlib.metadata as _metadata

__all__ = ["entry_points"]


def entry_points(*, group: str) -> _metadata.EntryPoints:
    if sys.version_info >= (3, 10):
        return _metadata.entry_points(group=group)

    epg = _metadata.entry_points()

    if sys.version_info < (3, 8) and hasattr(epg, "select"):
        return epg.select(group=group)  # type: ignore[no-any-return, no-untyped-call]

    return epg.get(group, [])  # type: ignore[no-any-return, attr-defined]


def __dir__() -> list[str]:
    return __all__
