from __future__ import annotations

import functools
import logging

from .._logging import logger

__all__ = ["setup_logging"]


def __dir__() -> list[str]:
    return __all__


@functools.lru_cache(1)
def setup_logging(log_level: str) -> None:
    level_value = {
        "CRITICAL": logging.CRITICAL,
        "ERROR": logging.ERROR,
        "WARNING": logging.WARNING,
        "INFO": logging.INFO,
        "DEBUG": logging.DEBUG,
        "NOTSET": logging.NOTSET,
    }[log_level]

    ch = logging.StreamHandler()
    ch.setLevel(level_value)
    # create formatter and add it to the handlers
    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    ch.setFormatter(formatter)
    # add the handlers to the logger
    logger.addHandler(ch)
