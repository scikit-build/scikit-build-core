from __future__ import annotations

import sys
import typing

if sys.version_info < (3, 8):
    from typing_extensions import (
        Literal,
        Protocol,
        get_args,
        get_origin,
    )
else:
    from typing import Literal, Protocol, get_args, get_origin

if sys.version_info < (3, 11):
    if typing.TYPE_CHECKING:
        from typing_extensions import Self
    else:
        Self = object
else:
    from typing import Self

__all__ = ["Protocol", "Literal", "Self", "get_origin", "get_args"]


def __dir__() -> list[str]:
    return __all__
