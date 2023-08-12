from __future__ import annotations

from .._compat.importlib import resources as _resources

__all__ = ["resources"]


resources = _resources.files(__name__)
