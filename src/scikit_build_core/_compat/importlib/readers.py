from __future__ import annotations

import sys
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path

if sys.version_info < (3, 10):
    # Readers and MultiplexedPath were introduced in 3.10, so nothing should output a MultiplexedPath
    # It is also tricky because it is unclear if the `resource_loader` when calling `import` would create
    # either importlib.readers.MultiplexedPath or importlib_resources.MultiplexedPath.
    # Creating a dummy class instead so that if it fails, it fails completely (and mypy is made happy)
    class MultiplexedPath:
        _paths: list[Path]
else:
    # From 3.11 this is an alias of importlib.resources.readers
    from importlib.readers import MultiplexedPath

__all__ = ["MultiplexedPath"]


def __dir__() -> list[str]:
    return __all__
