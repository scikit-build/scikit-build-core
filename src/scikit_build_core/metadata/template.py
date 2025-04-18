from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import Mapping

from . import _process_dynamic_metadata

__all__ = ["dynamic_metadata", "dynamic_metadata_needs"]


def __dir__() -> list[str]:
    return __all__


KEYS = {"needs", "result"}


def dynamic_metadata(
    field: str,
    settings: Mapping[str, str | list[str] | dict[str, str] | dict[str, list[str]]],
    metadata: Mapping[str, Any],
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
        lambda r: r.format(**metadata),
        result,
    )


def dynamic_metadata_needs(
    field: str,  # noqa: ARG001
    settings: Mapping[str, Any],
) -> list[str]:
    return settings.get("needs", [])
