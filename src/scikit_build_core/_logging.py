from __future__ import annotations

import logging
import sys
from typing import Any

__all__ = ["logger", "raw_logger", "ScikitBuildLogger"]


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


logger = ScikitBuildLogger(raw_logger)
