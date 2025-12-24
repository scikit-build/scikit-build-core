from __future__ import annotations

import sys
import typing

if sys.version_info < (3, 9):
    from typing_extensions import Annotated, get_args, get_origin
else:
    from typing import Annotated, get_args, get_origin

if sys.version_info < (3, 10):
    from typing_extensions import TypeAlias
else:
    from typing import TypeAlias

if sys.version_info < (3, 11):
    if typing.TYPE_CHECKING:
        from typing_extensions import Self, assert_never
    else:
        Self = object

        def assert_never(_: object) -> None:
            msg = "Expected code to be unreachable"
            raise AssertionError(msg)
else:
    from typing import Self, assert_never

if sys.version_info < (3, 13):
    if typing.TYPE_CHECKING:
        from typing_extensions import TypeVar
    else:

        # The final noqa is a false positive, see https://github.com/astral-sh/ruff/issues/22178
        def TypeVar(  # noqa: N802
            *args: object,
            default: object = None,  # noqa: ARG001
            **kwargs: object,  # noqa: ARG001
        ) -> typing.TypeVar:
            return typing.TypeVar(*args, **kwargs)
else:
    from typing import TypeVar


__all__ = [
    "Annotated",
    "Self",
    "TypeAlias",
    "TypeVar",
    "assert_never",
    "get_args",
    "get_origin",
]


def __dir__() -> list[str]:
    return __all__
