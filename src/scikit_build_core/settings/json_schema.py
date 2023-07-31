from __future__ import annotations

import dataclasses
import typing
from typing import Any

from .._compat.typing import get_args, get_origin
from .documentation import pull_docs

__all__ = ["to_json_schema"]


def __dir__() -> list[str]:
    return __all__


def to_json_schema(dclass: type[Any], *, normalize_keys: bool) -> dict[str, Any]:
    assert dataclasses.is_dataclass(dclass)
    props = {}
    unknown = []
    for field in dataclasses.fields(dclass):
        if dataclasses.is_dataclass(field.type):
            props[field.name] = to_json_schema(
                field.type, normalize_keys=normalize_keys
            )
            continue
        current_type = field.type
        origin = get_origin(current_type)
        args = get_args(current_type)
        if (
            origin is typing.Union
            and len(args) == 2
            and any(a is type(None) for a in args)
        ):
            current_type = next(iter(a for a in args if a is not type(None)))
            origin = get_origin(current_type)
            args = get_args(current_type)

        if origin is list and args[0] is str:
            props[field.name] = {"type": "array", "items": {"type": "string"}}
        elif origin is dict and args[0] is str and args[1] is str:
            props[field.name] = {
                "type": "object",
                "patternProperties": {".+": {"type": "string"}},
            }
        elif origin is dict and args[0] is str and get_origin(args[1]) is dict:
            props[field.name] = {
                "type": "object",
                "patternProperties": {".+": {"type": "object"}},
            }
        elif current_type == str:
            props[field.name] = {"type": "string"}
        elif current_type == bool:
            props[field.name] = {"type": "boolean"}
        else:
            unknown.append(
                (
                    field.name,
                    field.type,
                    get_origin(field.type),
                    get_args(field.type),
                )
            )
            continue

        if field.default is not dataclasses.MISSING and field.default is not None:
            props[field.name]["default"] = field.default

    assert not unknown, f"{unknown} left over!"

    docs = pull_docs(dclass)
    for k, v in docs.items():
        props[k]["description"] = v

    if normalize_keys:
        props = {k.replace("_", "-"): v for k, v in props.items()}

    return {"type": "object", "additionalProperties": False, "properties": props}
