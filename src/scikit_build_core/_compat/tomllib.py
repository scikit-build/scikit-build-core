from __future__ import annotations

import sys

if sys.version_info < (3, 11):
    from tomli import load
else:
    from tomllib import load

__all__ = ["load"]


def __dir__() -> list[str]:
    return __all__
