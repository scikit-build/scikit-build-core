from __future__ import annotations

from importlib.resources import files

__all__ = ["resources"]


resources = files(__name__)
