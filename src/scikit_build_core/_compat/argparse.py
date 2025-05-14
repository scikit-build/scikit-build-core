from __future__ import annotations

import argparse
import functools
import sys

__all__ = ["ArgumentParser"]


def __dir__() -> list[str]:
    return __all__


ArgumentParser = functools.partial(argparse.ArgumentParser)

if sys.version_info >= (3, 14):
    ArgumentParser = functools.partial(
        ArgumentParser, color=True, suggest_on_error=True
    )
