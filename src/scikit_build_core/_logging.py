from __future__ import annotations

import contextlib
import logging
import os
import re
import sys
from typing import Any

__all__ = ["logger", "raw_logger", "ScikitBuildLogger", "rich_print"]


def __dir__() -> list[str]:
    return __all__


raw_logger = logging.getLogger(
    "scikit_build_core"
)  # TODO: maybe should be scikit-build?
raw_logger.setLevel(logging.DEBUG)  # TODO: configure


class FStringMessage:
    "This class captures a formatted string message and only produces it on demand."

    def __init__(self, fmt: str, *args: object, **kwargs: object) -> None:
        self.fmt = fmt
        self.args = args
        self.kwargs = kwargs

    def __str__(self) -> str:
        return self.fmt.format(*self.args, **self.kwargs)

    def __repr__(self) -> str:
        return (
            f"<FStringMessage {self.fmt!r} args={self.args!r} kwargs={self.kwargs!r}>"
        )


if sys.version_info < (3, 8):
    opts: Any = {}
else:
    opts = {"stacklevel": 2}


class ScikitBuildLogger:
    # pylint: disable-next=redefined-outer-name
    def __init__(self, logger: logging.Logger) -> None:
        self.logger = logger

    def debug(self, msg: str, *args: object, **kwargs: object) -> None:
        self.logger.debug(FStringMessage(msg, *args, **kwargs), **opts)

    def info(self, msg: str, *args: object, **kwargs: object) -> None:
        self.logger.info(FStringMessage(msg, *args, **kwargs), **opts)

    def warning(self, msg: str, *args: object, **kwargs: object) -> None:
        self.logger.warning(FStringMessage(msg, *args, **kwargs), **opts)

    def error(self, msg: str, *args: object, **kwargs: object) -> None:
        self.logger.error(FStringMessage(msg, *args, **kwargs), **opts)

    def critical(self, msg: str, *args: object, **kwargs: object) -> None:
        self.logger.critical(FStringMessage(msg, *args, **kwargs), **opts)

    def exception(self, msg: str, *args: object, **kwargs: object) -> None:
        self.logger.exception(FStringMessage(msg, *args, **kwargs), **opts)

    def log(self, level: int, msg: str, *args: object, **kwargs: object) -> None:
        self.logger.log(level, FStringMessage(msg, *args, **kwargs), **opts)

    def setLevel(self, level: int) -> None:
        self.logger.setLevel(level)

    def addHandler(self, handler: logging.Handler) -> None:
        self.logger.addHandler(handler)


logger = ScikitBuildLogger(raw_logger)


ANY_ESCAPE = re.compile(r"\[([\w\s/]*)\]")


_COLORS = {
    "red": "\33[91m",
    "green": "\33[92m",
    "yellow": "\33[93m",
    "blue": "\33[94m",
    "magenta": "\33[95m",
    "cyan": "\33[96m",
    "bold": "\33[1m",
    "/red": "\33[0m",
    "/green": "\33[0m",
    "/blue": "\33[0m",
    "/yellow": "\33[0m",
    "/magenta": "\33[0m",
    "/cyan": "\33[0m",
    "/bold": "\33[22m",
    "reset": "\33[0m",
}
_NO_COLORS = {color: "" for color in _COLORS}


def colors() -> dict[str, str]:
    if "NO_COLOR" in os.environ:
        return _NO_COLORS
    # Pip reroutes sys.stdout, so FORCE_COLOR is required there
    if os.environ.get("FORCE_COLOR", ""):
        return _COLORS
    # Avoid ValueError: I/O operation on closed file
    with contextlib.suppress(ValueError):
        # Assume sys.stderr is similar to sys.stdout
        isatty = sys.stdout.isatty()
        if isatty and not sys.platform.startswith("win"):
            return _COLORS
    return _NO_COLORS


def _process_rich(msg: object) -> str:
    return ANY_ESCAPE.sub(
        lambda m: "".join(colors()[x] for x in m.group(1).split()),
        str(msg),
    )


def rich_print(*args: object, **kwargs: object) -> None:
    args_2 = tuple(_process_rich(arg) for arg in args)
    if args != args_2:
        args_2 = (*args_2[:-1], args_2[-1] + colors()["reset"])
    print(*args_2, **kwargs, flush=True)  # type: ignore[call-overload] # noqa: T201
