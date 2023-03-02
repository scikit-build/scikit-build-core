from __future__ import annotations

import sys

if sys.version_info < (3, 9):
    import importlib_resources as resources
else:
    from importlib import resources

__all__ = ["resources"]


def __dir__() -> list[str]:
    return __all__
