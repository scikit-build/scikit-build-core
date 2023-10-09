from __future__ import annotations

import importlib.util

if not importlib.util.find_spec("click"):
    msg = "Missing cli dependencies. Make sure scikit-build-core is installed with [cli] optional dependency"
    raise ImportError(msg)

from .main import skbuild

__all__: list[str] = ["skbuild"]
