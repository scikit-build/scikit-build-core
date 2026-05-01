from __future__ import annotations

from typing import Any

try:
    from setuptools.errors import SetupError
except (ImportError, AttributeError):
    from distutils.errors import DistutilsSetupError

    SetupError: Any = DistutilsSetupError  # type: ignore[no-redef]

__all__ = ["SetupError"]


def __dir__() -> list[str]:
    return __all__
