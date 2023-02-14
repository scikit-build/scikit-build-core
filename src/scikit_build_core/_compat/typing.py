from __future__ import annotations

import sys
import typing

if sys.version_info < (3, 8):
    from typing_extensions import Literal, Protocol, runtime_checkable
else:
    from typing import Literal, Protocol, runtime_checkable

if sys.version_info < (3, 11):
    if typing.TYPE_CHECKING:
        from typing_extensions import Self
    else:
        Self = object
else:
    from typing import Self

__all__ = ["Protocol", "runtime_checkable", "Literal", "Self"]


def __dir__() -> list[str]:
    return __all__
