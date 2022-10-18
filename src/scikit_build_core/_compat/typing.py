from __future__ import annotations

import sys

if sys.version_info < (3, 8):
    from typing_extensions import Protocol, runtime_checkable
else:
    from typing import Protocol, runtime_checkable

__all__ = ["Protocol", "runtime_checkable"]


def __dir__() -> list[str]:
    return __all__
