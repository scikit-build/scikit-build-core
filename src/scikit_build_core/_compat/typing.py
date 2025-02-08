from __future__ import annotations

import sys
import typing

if sys.version_info < (3, 9):
    from typing_extensions import Annotated, get_args, get_origin
else:
    from typing import Annotated, get_args, get_origin

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

__all__ = [
    "Annotated",
    "Self",
    "assert_never",
    "get_args",
    "get_origin",
]


def __dir__() -> list[str]:
    return __all__
