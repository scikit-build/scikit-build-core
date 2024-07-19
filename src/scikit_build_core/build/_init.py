from __future__ import annotations

import functools
import logging

from .._logging import LEVEL_VALUE, logger

__all__ = ["setup_logging"]


def __dir__() -> list[str]:
    return __all__


@functools.lru_cache(1)
def setup_logging(log_level: str) -> None:
    level_value = LEVEL_VALUE[log_level]
    logger.setLevel(level_value)

    ch = logging.StreamHandler()
    # create formatter and add it to the handlers
    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    ch.setFormatter(formatter)
    # add the handlers to the logger
    logger.addHandler(ch)
