from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from .._compat.importlib import metadata, resources

__all__: list[str] = ["get_cmake_modules"]


def __dir__() -> list[str]:
    return __all__


def get_cmake_modules(select: Callable[[str], bool] = lambda _: True) -> list[Path]:
    module_dirs = metadata.entry_points(group="cmake.modules")
    return [resources.files(ep.load()) for ep in module_dirs if select(ep.name)]
