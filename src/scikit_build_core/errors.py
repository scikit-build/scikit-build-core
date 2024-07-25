from __future__ import annotations

import textwrap
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import subprocess

__all__ = [
    "CMakeAccessError",
    "CMakeConfigError",
    "CMakeNotFoundError",
    "CMakeVersionError",
    "FailedLiveProcessError",
    "FailedProcessError",
    "NinjaNotFoundError",
    "NinjaVersionError",
    "NotFoundError",
    "ScikitBuildError",
]


def __dir__() -> list[str]:
    return __all__


class ScikitBuildError(Exception):
    """
    Base class for all ScikitBuildError errors.
    """


class NotFoundError(ScikitBuildError):
    """
    Raised when a program is not found.
    """


class CMakeNotFoundError(NotFoundError):
    """
    Raised when cmake is not found.
    """


class NinjaNotFoundError(NotFoundError):
    """
    Raised when ninja is not found.
    """


class FailedProcessError(Exception):
    """
    Exception raised when an call fails.
    """

    def __init__(
        self, exception: subprocess.CalledProcessError, description: str
    ) -> None:
        super().__init__()
        self.exception = exception
        self._description = description

    def __str__(self) -> str:
        cmd = " ".join(self.exception.cmd)
        description = f"{self._description}\n  Command {cmd!r} failed with return code {self.exception.returncode}"
        for stream_name in ("stdout", "stderr"):
            stream = getattr(self.exception, stream_name)
            if stream:
                description += f"\n  {stream_name}:\n"
                description += textwrap.indent(stream.decode(), "    ")
        return description


class FailedLiveProcessError(Exception):
    """
    Exception for when output was not being redirected.
    """

    def __init__(self, *args: object, msg: str = "") -> None:
        super().__init__(*args)
        self.msg = msg


class CMakeAccessError(FailedProcessError):
    """
    Error raised when CMake access fails.
    """


class CMakeVersionError(ScikitBuildError):
    """
    Error raised when CMake version is not supported.
    """


class NinjaVersionError(ScikitBuildError):
    """
    Error raised when CMake version is not supported.
    """


class CMakeConfigError(ScikitBuildError):
    """
    Something is misconfigured.
    """
