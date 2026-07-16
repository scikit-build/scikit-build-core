from __future__ import annotations

__lazy_modules__ = {"importlib", "importlib.resources"}

from importlib.resources import files

__all__ = ["files"]


def __dir__() -> list[str]:
    return __all__
