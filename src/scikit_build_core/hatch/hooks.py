from __future__ import annotations

from typing import Any

from hatchling.plugin import hookimpl

from .plugin import ScikitBuildHook

__all__ = ["hatch_register_build_hook"]


def __dir__() -> list[str]:
    return __all__


@hookimpl
def hatch_register_build_hook() -> Any:
    return ScikitBuildHook
