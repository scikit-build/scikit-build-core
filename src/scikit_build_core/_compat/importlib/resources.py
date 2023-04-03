from __future__ import annotations

import sys

if sys.version_info < (3, 9):
    from importlib_resources import files
else:
    from importlib.resources import files

__all__ = ["files"]


def __dir__() -> list[str]:
    return __all__
