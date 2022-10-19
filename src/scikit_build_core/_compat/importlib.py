from __future__ import annotations

import sys
from pathlib import Path

if sys.version_info < (3, 10):
    import importlib_metadata as metadata
else:
    from importlib import metadata

if sys.version_info < (3, 9):
    import importlib_resources as resources
else:
    from importlib import resources

if sys.version_info >= (3, 11):
    from importlib.resources.abc import Traversable
elif sys.version_info >= (3, 9):
    from importlib.abc import Traversable
else:
    Traversable = Path

__all__ = ["metadata", "resources", "Traversable"]


def __dir__() -> list[str]:
    return __all__
