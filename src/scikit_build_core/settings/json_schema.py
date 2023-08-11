from __future__ import annotations

import dataclasses
import sys
from pathlib import Path
from typing import Any, Union

from packaging.version import Version

from .._compat.builtins import ExceptionGroup
from .._compat.typing import Literal, get_args, get_origin
from .documentation import pull_docs

__all__ = ["to_json_schema", "convert_type", "FailedConversion"]


def __dir__() -> list[str]:
    return __all__


class FailedConversion(TypeError):
    pass


def to_json_schema(dclass: type[Any], *, normalize_keys: bool) -> dict[str, Any]:
    assert dataclasses.is_dataclass(dclass)
    props = {}
    errs = []
    required = []
    for field in dataclasses.fields(dclass):
        if dataclasses.is_dataclass(field.type):
            props[field.name] = to_json_schema(
                field.type, normalize_keys=normalize_keys
            )
            continue

        try:
            props[field.name] = convert_type(field.type, normalize_keys=normalize_keys)
        except FailedConversion as err:
            if sys.version_info < (3, 11):
                notes = "__notes__"  # set so linter's won't try to be clever
                setattr(err, notes, [*getattr(err, notes, []), f"Field: {field.name}"])
            else:
                # pylint: disable-next=no-member
                err.add_note(f"Field: {field.name}")
            errs.append(err)
            continue

        if field.default is not dataclasses.MISSING and field.default is not None:
            props[field.name]["default"] = (
                str(field.default)
                if isinstance(field.default, (Version, Path))
                else field.default
            )

        if (
            field.default_factory is dataclasses.MISSING
            and field.default is dataclasses.MISSING
        ):
            required.append(field.name)

    if errs:
        msg = f"Failed Conversion to JSON Schema on {dclass.__name__}"
        raise ExceptionGroup(msg, errs)

    docs = pull_docs(dclass)
    for k, v in docs.items():
        props[k]["description"] = v

    if normalize_keys:
        props = {k.replace("_", "-"): v for k, v in props.items()}

    if required:
        return {
            "type": "object",
            "additionalProperties": False,
            "required": required,
            "properties": props,
        }

    return {"type": "object", "additionalProperties": False, "properties": props}


def convert_type(t: Any, *, normalize_keys: bool) -> dict[str, Any]:
    if dataclasses.is_dataclass(t):
        return to_json_schema(t, normalize_keys=normalize_keys)
    if t is str or t is Path or t is Version:
        return {"type": "string"}
    if t is bool:
        return {"type": "boolean"}
    origin = get_origin(t)
    args = get_args(t)
    if origin is list:
        assert len(args) == 1
        return {
            "type": "array",
            "items": convert_type(args[0], normalize_keys=normalize_keys),
        }
    if origin is dict:
        assert len(args) == 2
        assert args[0] is str
        if args[1] is Any:
            return {"type": "object"}
        return {
            "type": "object",
            "patternProperties": {
                ".+": convert_type(args[1], normalize_keys=normalize_keys)
            },
        }
    if origin is Union:
        # Ignore optional
        if len(args) == 2 and any(a is type(None) for a in args):
            return convert_type(
                next(iter(a for a in args if a is not type(None))),
                normalize_keys=normalize_keys,
            )
        return {"oneOf": [convert_type(a, normalize_keys=normalize_keys) for a in args]}
    if origin is Literal:
        return {"enum": list(args)}

    msg = f"Cannot convert type {t} to JSON Schema"
    raise FailedConversion(msg)
