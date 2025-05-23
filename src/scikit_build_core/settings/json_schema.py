from __future__ import annotations

import dataclasses
import sys
from pathlib import Path
from typing import Any, Literal, Union

from packaging.specifiers import SpecifierSet
from packaging.version import Version

from .._compat.builtins import ExceptionGroup
from .._compat.typing import Annotated, get_args, get_origin
from .documentation import pull_docs

__all__ = ["FailedConversionError", "convert_type", "to_json_schema"]


def __dir__() -> list[str]:
    return __all__


class FailedConversionError(TypeError):
    pass


def to_json_schema(dclass: type[Any], *, normalize_keys: bool) -> dict[str, Any]:
    assert dataclasses.is_dataclass(dclass)
    props = {}
    errs = []
    required = []
    for field in dataclasses.fields(dclass):
        field_type = field.type
        if dataclasses.is_dataclass(field.type) and isinstance(field_type, type):
            props[field.name] = to_json_schema(
                field_type, normalize_keys=normalize_keys
            )
            continue

        if get_origin(field.type) is Annotated:
            if get_args(field.type)[1] == "EnvVar":
                full = convert_type(
                    get_args(field.type)[0], normalize_keys=normalize_keys
                )
                types = full["patternProperties"][".+"]
                full["patternProperties"][".+"] = {
                    "oneOf": [
                        types,
                        {
                            "type": "object",
                            "additionalProperties": False,
                            "required": ["env"],
                            "properties": {
                                "env": {"type": "string", "minLength": 1},
                                "default": types,
                            },
                        },
                    ]
                }
                props[field.name] = full
                continue
            msg = "Only EnvVar is supported for Annotated"
            raise FailedConversionError(msg)

        try:
            props[field.name] = convert_type(field.type, normalize_keys=normalize_keys)
        except FailedConversionError as err:
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
                if isinstance(field.default, (Version, Path, SpecifierSet))
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
    for field in dataclasses.fields(dclass):
        if field.name not in docs:
            continue
        props[field.name]["description"] = docs[field.name].split("\n", maxsplit=1)[0]
        if field.metadata.get("deprecated"):
            props[field.name]["deprecated"] = True

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
    if dataclasses.is_dataclass(t) and isinstance(t, type):
        return to_json_schema(t, normalize_keys=normalize_keys)
    if t is str or t is Path or t is Version or t is SpecifierSet:
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
        return {
            "oneOf": [
                convert_type(a, normalize_keys=normalize_keys)
                for a in args
                if a is not type(None)
            ]
        }
    if origin is Literal:
        return {"enum": list(args)}
    if hasattr(t, "json_schema"):
        return convert_type(t.json_schema, normalize_keys=normalize_keys)

    msg = f"Cannot convert type {t} to JSON Schema"
    raise FailedConversionError(msg)
