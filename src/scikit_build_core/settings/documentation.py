from __future__ import annotations

import ast
import dataclasses
import inspect
import textwrap
import typing
from pathlib import Path

from packaging.specifiers import SpecifierSet
from packaging.version import Version

from .. import __version__
from .._compat.typing import Annotated, get_args, get_origin

if typing.TYPE_CHECKING:
    from collections.abc import Generator


__all__ = ["pull_docs"]


def __dir__() -> list[str]:
    return __all__


version_display = ".".join(__version__.split(".")[:2])


def _get_value(value: ast.expr) -> str:
    assert isinstance(value, ast.Constant)
    assert isinstance(value.value, str)
    return value.value


def pull_docs(dc: type[object]) -> dict[str, str]:
    """
    Pulls documentation from a dataclass.
    """
    t = ast.parse(inspect.getsource(dc))
    (obody,) = t.body
    assert isinstance(obody, ast.ClassDef)
    body = obody.body
    return {
        assign.target.id: textwrap.dedent(_get_value(expr.value)).strip()  # type: ignore[union-attr]
        for assign, expr in zip(body[:-1], body[1:])
        if isinstance(assign, ast.AnnAssign) and isinstance(expr, ast.Expr)
    }


@dataclasses.dataclass(frozen=True)
class DCDoc:
    name: str
    type: str
    default: str
    docs: str
    field: dataclasses.Field[typing.Any]
    deprecated: bool = False


def sanitize_default_field(text: str) -> str:
    return text.replace("'", '"').replace("True", "true").replace("False", "false")


def is_optional(field: type) -> bool:
    return get_origin(field) is typing.Union and type(None) in get_args(field)


def get_display_type(field_type: type | str) -> str:
    if isinstance(field_type, str):
        return field_type
    if is_optional(field_type):
        # Special case for optional, we just take the first part
        return get_display_type(get_args(field_type)[0])
    # Handle built-ins
    if get_origin(field_type) is dict:
        key_display = get_display_type(get_args(field_type)[0])
        val_display = get_display_type(get_args(field_type)[1])
        return f"dict[{key_display},{val_display}]"
    if get_origin(field_type) is list:
        return f"list[{get_display_type(get_args(field_type)[0])}]"
    # Handle other typing specials
    if get_origin(field_type) is typing.Literal:
        return " | ".join(f'"{x}"' for x in get_args(field_type))
    if get_origin(field_type) is Annotated:
        # For annotated assume we always want the second item
        return get_display_type(get_args(field_type)[1])
    if field_type is typing.Any:
        # Workaround for python<3.10 where typing.Any.__name__ does not evaluate
        return "Any"
    # Otherwise just get the formatted form of the `type` object
    return field_type.__name__


def mk_docs(dc: type[object], prefix: str = "") -> Generator[DCDoc, None, None]:
    """
    Makes documentation for a dataclass.
    """
    assert dataclasses.is_dataclass(dc)
    docs = pull_docs(dc)

    for field in dataclasses.fields(dc):
        field_type = field.type
        if dataclasses.is_dataclass(field_type) and isinstance(field_type, type):
            yield from mk_docs(field_type, prefix=f"{prefix}{field.name}.")
            continue

        if get_origin(field.type) is list:
            field_type = get_args(field.type)[0]
            if dataclasses.is_dataclass(field_type) and isinstance(field_type, type):
                yield from mk_docs(field_type, prefix=f"{prefix}{field.name}[].")
                continue

        if default_before_format := field.metadata.get("display_default", None):
            assert isinstance(default_before_format, str)
            default = default_before_format.format(
                version=version_display,
            )
        elif field.default is not dataclasses.MISSING and field.default is not None:
            default = repr(
                str(field.default)
                if isinstance(field.default, (Path, Version, SpecifierSet))
                else field.default
            )
        elif field.default_factory is not dataclasses.MISSING:
            default = repr(field.default_factory())
        else:
            default = '""'

        yield DCDoc(
            name=f"{prefix}{field.name}".replace("_", "-"),
            type=field.metadata.get("display_type", get_display_type(field.type)),
            default=sanitize_default_field(default),
            docs=docs[field.name],
            field=field,
            deprecated=field.metadata.get("deprecated", False),
        )
