from __future__ import annotations

import sys
from typing import Any, Union

from .._compat.typing import Annotated, get_args, get_origin

__all__ = [
    "get_inner_type",
    "get_target_raw_type",
    "is_union_type",
    "process_annotated",
    "process_union",
]


def __dir__() -> list[str]:
    return __all__


# Runtime check for PEP 604 union syntax (A | B) support
# types.UnionType only exists in Python 3.10+
if sys.version_info >= (3, 10):
    from types import NoneType
    from types import UnionType as _UnionType
else:
    NoneType = type(None)

    class _UnionType:
        pass


def process_union(target: Any, /) -> Any:
    """
    Filters None out of Unions. If a Union only has one item, return that item.
    """

    origin = get_origin(target)

    if is_union_type(origin):
        non_none_args = [a for a in get_args(target) if a is not NoneType]
        if len(non_none_args) == 1:
            return non_none_args[0]
        return Union[tuple(non_none_args)]

    return target


def process_annotated(target: type[Any], /) -> tuple[Any, tuple[Any, ...]]:
    """
    Splits annotated into raw type and annotations. If not annotated, the annotations will be empty.
    """

    origin = get_origin(target)
    if origin is Annotated:
        return get_args(target)[0], get_args(target)[1:]

    return target, ()


def get_target_raw_type(target: type[Any] | Any, /) -> Any:
    """
    Takes a type like ``Optional[str]`` and returns str, or ``Optional[Dict[str,
    int]]`` and returns dict. Returns Union for a Union with more than one
    non-none type. Literal is also a valid return. Works through Annotated.
    """

    target, _ = process_annotated(target)
    target = process_union(target)
    origin = get_origin(target)
    return origin or target


def is_union_type(raw_target: Any) -> bool:
    """
    Check if raw_target is a Union type (either ``typing.Union`` or ``types.UnionType``).
    Handles both ``typing.Union[A, B]`` and PEP 604 syntax (``A | B``).
    """
    return raw_target is Union or raw_target is _UnionType


def get_inner_type(_target: type[Any], /) -> type[Any]:
    """
    Takes a type like ``list[str]`` and returns str,
    or ``dict[str, int]`` and returns int.
    """

    raw_target = get_target_raw_type(_target)
    target = process_union(_target)
    if raw_target is list:
        return get_args(target)[0]  # type: ignore[no-any-return]
    if raw_target is dict:
        return get_args(target)[1]  # type: ignore[no-any-return]
    msg = f"Expected a list or dict, got {target!r}"
    raise AssertionError(msg)
