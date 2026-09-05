from __future__ import annotations

import functools
import importlib.metadata
import sys

TYPE_CHECKING = False

if TYPE_CHECKING:
    if sys.version_info < (3, 10):
        from importlib.metadata import EntryPoint

        EntryPoints = list[EntryPoint]
    elif sys.version_info < (3, 12):
        from importlib.metadata import EntryPoints, SelectableGroups
    else:
        from importlib.metadata import EntryPoints

        SelectableGroups = EntryPoints

__all__ = ["all_entry_points", "entry_points"]


if sys.version_info >= (3, 10):

    @functools.cache
    def all_entry_points() -> SelectableGroups:
        """Scan the installed distributions once; every group shares the result.

        Call ``all_entry_points.cache_clear()`` if the entry points change.
        """
        return importlib.metadata.entry_points()

    def entry_points(*, group: str) -> EntryPoints:
        """Entry points for one group, from the cached scan.

        Callers read this from the module global, so a monkeypatch of it is seen.
        """
        return all_entry_points().select(group=group)

else:

    @functools.cache
    def all_entry_points() -> dict[str, EntryPoints]:
        return importlib.metadata.entry_points()

    def entry_points(*, group: str) -> EntryPoints:
        return all_entry_points().get(group, [])  # pylint: disable=no-member


def __dir__() -> list[str]:
    return __all__
