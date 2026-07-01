from __future__ import annotations

import typing

TYPE_CHECKING = False

if TYPE_CHECKING:
    from collections.abc import Callable, Mapping
    from typing import Any


__all__: list[str] = [
    "_ALL_FIELDS",
    "_EXTENDABLE_FIELDS",
    "_SCALAR_FIELDS",
    "_process_dynamic_metadata",
    "_require_field",
]


# Name is not dynamically settable, so not in this list
_STR_FIELDS = frozenset(
    [
        "version",
        "description",
        "requires-python",
        "license",
    ]
)

# Dynamic is not dynamically settable, so not in this list
_LIST_STR_FIELDS = frozenset(
    [
        "classifiers",
        "keywords",
        "dependencies",
        "license-files",
    ]
)

_DICT_STR_FIELDS = frozenset(
    [
        "urls",
        "scripts",
        "gui-scripts",
    ]
)

_LIST_DICT_FIELDS = frozenset(
    [
        "authors",
        "maintainers",
    ]
)

# Single-value fields: a later entry replaces the value rather than extending
# it, and PEP 808 forbids giving them both statically and dynamically.
_SCALAR_FIELDS = _STR_FIELDS | frozenset(["readme"])

# "dynamic" and "name" can't be set or requested
_ALL_FIELDS = (
    _STR_FIELDS
    | _LIST_STR_FIELDS
    | _DICT_STR_FIELDS
    | _LIST_DICT_FIELDS
    | frozenset(
        [
            "optional-dependencies",
            "readme",
            "entry-points",
        ]
    )
)

# Fields PEP 808 allows to be given statically in [project] *and* listed in
# dynamic, so a provider may add to the static portion: everything except the
# scalar fields, which hold a single value and so cannot be extended.
_EXTENDABLE_FIELDS = _ALL_FIELDS - _SCALAR_FIELDS

T = typing.TypeVar(
    "T",
    bound="str | list[str] | list[dict[str, str]] | dict[str, str] | dict[str, list[str]] | dict[str, dict[str, str]]",
)


def _require_field(
    settings: Mapping[str, Any], *, default: str | None = None
) -> tuple[str, dict[str, Any]]:
    """Split the target ``field`` out of new-style (0.3) plugin settings.

    The ``[[tool.dynamic-metadata]]`` table has no field key of its own, so a
    single-value plugin names its target through a ``field`` setting. Returns the
    field name and the remaining settings (``field`` removed) to forward to the
    bundled legacy hook. ``default`` supplies the field for a fixed-target plugin
    (e.g. ``setuptools_scm`` only sets ``version``).
    """
    field: Any = settings.get("field", default)
    if not isinstance(field, str):
        # Usually a *missing* setting (None), not a wrong type, so not TypeError.
        msg = "This plugin requires a 'field' setting naming the target field"
        raise RuntimeError(msg)  # noqa: TRY004
    rest = {k: v for k, v in settings.items() if k != "field"}
    return field, rest


def _process_dynamic_metadata(field: str, action: Callable[[str], str], result: T) -> T:
    """
    Helper function for processing an action on the various possible metadata fields.
    """

    if field in _STR_FIELDS:
        if not isinstance(result, str):
            msg = f"Field {field!r} must be a string"
            raise RuntimeError(msg)
        return action(result)  # type: ignore[return-value]
    if field in _LIST_STR_FIELDS:
        if not (isinstance(result, list) and all(isinstance(r, str) for r in result)):
            msg = f"Field {field!r} must be a list of strings"
            raise RuntimeError(msg)
        return [action(r) for r in result]  # type: ignore[arg-type, return-value]
    if field in _DICT_STR_FIELDS | {"readme"}:
        if not isinstance(result, dict) or not all(
            isinstance(v, str) for v in result.values()
        ):
            msg = f"Field {field!r} must be a dictionary of strings"
            raise RuntimeError(msg)
        return {action(k): action(v) for k, v in result.items()}  # type: ignore[arg-type, return-value]
    if field in _LIST_DICT_FIELDS:
        if not isinstance(result, list) or not all(
            isinstance(d, dict)
            and all(isinstance(k, str) and isinstance(v, str) for k, v in d.items())  # type: ignore[redundant-expr]
            for d in result
        ):
            msg = f"Field {field!r} must be a list of dictionaries of strings"
            raise RuntimeError(msg)
        return [{k: action(v) for k, v in d.items()} for d in result]  # type: ignore[union-attr, return-value]
    if field == "entry-points":
        if not isinstance(result, dict) or not all(
            isinstance(d, dict)
            and all(isinstance(k, str) and isinstance(v, str) for k, v in d.items())  # type: ignore[redundant-expr]
            for d in result.values()
        ):
            msg = "Field 'entry-points' must be a dictionary of dictionary of strings"
            raise RuntimeError(msg)
        return {
            dk: {action(k): action(v) for k, v in dv.items()}  # type: ignore[union-attr]
            for dk, dv in result.items()
        }  # type: ignore[return-value]
    if field == "optional-dependencies":
        if not isinstance(result, dict) or not all(
            isinstance(v, list) and all(isinstance(r, str) for r in v)
            for v in result.values()
        ):
            msg = (
                "Field 'optional-dependencies' must be a dictionary of lists of strings"
            )
            raise RuntimeError(msg)
        return {k: [action(r) for r in v] for k, v in result.items()}  # type: ignore[return-value]

    msg = f"Unsupported field {field!r} for action"
    raise RuntimeError(msg)
