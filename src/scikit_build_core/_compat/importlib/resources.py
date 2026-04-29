from __future__ import annotations

from importlib.resources import files

__all__ = ["files"]


def __dir__() -> list[str]:
    return __all__
