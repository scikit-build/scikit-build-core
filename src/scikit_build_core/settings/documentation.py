from __future__ import annotations

import ast
import dataclasses
import inspect
import textwrap
from pathlib import Path
from typing import TYPE_CHECKING, TypeVar, cast

from packaging.specifiers import SpecifierSet
from packaging.version import Version

from .. import __version__
from .._compat.typing import get_args, get_origin

if TYPE_CHECKING:
    from collections.abc import Generator

T = TypeVar("T")
U = TypeVar("U")


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
        assign.target.id: textwrap.dedent(_get_value(expr.value))  # type: ignore[union-attr]
        .strip()
        .replace("\n", " ")
        for assign, expr in zip(body[:-1], body[1:])
        if isinstance(assign, ast.AnnAssign) and isinstance(expr, ast.Expr)
    }


@dataclasses.dataclass
class DCDoc:
    name: str
    default: str
    docs: str
    deprecated: bool = False

    def __str__(self) -> str:
        docs = "\n".join(f"# {s}" for s in textwrap.wrap(self.docs, width=78))
        return f"{docs}\n{self.name} = {self.default}\n"


def get_metadata_field(field: dataclasses.Field[U], field_name: str, default: T) -> T:
    if field_name in field.metadata:
        return cast("T", field.metadata[field_name])
    return default


def sanitize_default_field(text: str) -> str:
    text = text.replace("'", '"')
    text = text.replace("True", "true")
    text = text.replace("False", "false")
    return text  # noqa: RET504


def mk_docs(dc: type[object], prefix: str = "") -> Generator[DCDoc, None, None]:
    """
    Makes documentation for a dataclass.
    """
    assert dataclasses.is_dataclass(dc)
    docs = pull_docs(dc)

    for field in dataclasses.fields(dc):
        field_type = field.type
        if isinstance(field_type, type) and dataclasses.is_dataclass(field_type):
            yield from mk_docs(field_type, prefix=f"{prefix}{field.name}.")
            continue

        if get_origin(field.type) is list:
            field_type = get_args(field.type)[0]
            if isinstance(field_type, type) and dataclasses.is_dataclass(field_type):
                yield from mk_docs(field_type, prefix=f"{prefix}{field.name}[].")
                continue

        if default_before_format := get_metadata_field(field, "display_default", None):
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
            default=sanitize_default_field(default),
            docs=docs[field.name],
            deprecated=get_metadata_field(field, "deprecated", False),  # noqa: FBT003
        )
