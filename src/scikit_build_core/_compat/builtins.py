from __future__ import annotations

import sys

if sys.version_info < (3, 11):
    from exceptiongroup import ExceptionGroup
else:
    from builtins import ExceptionGroup

__all__ = ["ExceptionGroup"]


def __dir__() -> list[str]:
    return __all__
