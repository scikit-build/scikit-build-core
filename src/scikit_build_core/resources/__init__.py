from __future__ import annotations

from .._compat.importlib import resources as _resources

__all__: list[str] = ["resources"]


resources = _resources.files(__name__)
