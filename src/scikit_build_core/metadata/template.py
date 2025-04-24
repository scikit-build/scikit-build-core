from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import Mapping

from . import _process_dynamic_metadata

__all__ = ["dynamic_metadata"]


def __dir__() -> list[str]:
    return __all__


KEYS = {"result"}


def dynamic_metadata(
    field: str,
    settings: Mapping[str, str | list[str] | dict[str, str] | dict[str, list[str]]],
    project: Mapping[str, Any],
) -> str | list[str] | dict[str, str] | dict[str, list[str]]:
    if settings.keys() > KEYS:
        msg = f"Only {KEYS} settings allowed by this plugin"
        raise RuntimeError(msg)

    if "result" not in settings:
        msg = "Must contain the 'result' setting with a template substitution"
        raise RuntimeError(msg)

    result = settings["result"]

    return _process_dynamic_metadata(
        field,
        lambda r: r.format(project=project),
        result,
    )
