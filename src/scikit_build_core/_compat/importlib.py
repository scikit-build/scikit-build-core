from __future__ import annotations

import sys

if sys.version_info < (3, 9):
    import importlib_resources as resources
else:
    from importlib import resources

if sys.version_info < (3, 11):
    import importlib_metadata as metadata
else:
    from importlib import metadata

__all__ = ["metadata", "resources"]


def __dir__() -> list[str]:
    return __all__
