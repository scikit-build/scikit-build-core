from __future__ import annotations

__lazy_modules__ = {"typing"}

from typing import Any

from . import _process_dynamic_metadata, _require_field

TYPE_CHECKING = False
if TYPE_CHECKING:
    from collections.abc import Mapping

__all__ = ["Provider", "dynamic_metadata"]


def __dir__() -> list[str]:
    return __all__


KEYS = {"result"}


def dynamic_metadata(
    field: str,
    settings: Mapping[str, str | list[str] | dict[str, str] | dict[str, list[str]]],
    project: Mapping[str, Any],
) -> str | list[str] | dict[str, str] | dict[str, list[str]]:
    if settings.keys() - KEYS:
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


class Provider:
    """New-style (dynamic-metadata 0.3) wrapper around :func:`dynamic_metadata`.

    Registered as the ``scikit_build_core.metadata.template`` entry point; the
    target field comes from a ``field`` setting instead of the legacy table key.
    """

    @staticmethod
    def dynamic_metadata(
        settings: Mapping[str, Any],
        project: Mapping[str, Any],
    ) -> dict[str, Any]:
        field, rest = _require_field(settings)
        return {field: dynamic_metadata(field, rest, project)}
