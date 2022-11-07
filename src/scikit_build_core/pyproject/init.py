from __future__ import annotations

import functools
import logging

__all__ = ["setup_logging"]


def __dir__() -> list[str]:
    return __all__


@functools.lru_cache(1)
def setup_logging(log_level: str) -> None:

    try:
        import rich.logging
        import rich.traceback
    except ModuleNotFoundError:
        logging.basicConfig(level=log_level)
        return

    FORMAT = "%(message)s"
    logging.basicConfig(
        level=log_level,
        format=FORMAT,
        datefmt="[%X]",
        handlers=[rich.logging.RichHandler(level=log_level, rich_tracebacks=True)],
    )

    rich.traceback.install()
