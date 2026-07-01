from __future__ import annotations

TYPE_CHECKING = False

if TYPE_CHECKING:
    from setuptools.errors import SetupError
else:
    try:
        from setuptools.errors import SetupError
    except ImportError:
        # pylint: disable-next=deprecated-module
        from distutils.errors import (
            DistutilsError as SetupError,  # type: ignore[assignment, misc]
        )

__all__ = ["SetupError"]


def __dir__() -> list[str]:
    return __all__
