from __future__ import annotations

import functools
import pathlib
from typing import TYPE_CHECKING

import click

if TYPE_CHECKING:
    from collections.abc import Callable
    from typing import Any, TypeVar

    F = TypeVar("F", bound=Callable[..., Any])


__all__: list[str] = ["_build_dir"]


def __dir__() -> list[str]:
    return __all__


def _build_dir(func: F) -> F:
    """Add build_dir click option"""

    @click.option(
        "--build-dir",
        "-B",
        type=click.Path(
            exists=True,
            file_okay=False,
            dir_okay=True,
            writable=True,
            path_type=pathlib.Path,
        ),
        help="Path to cmake build directory",
    )
    @functools.wraps(func)
    # TODO: Fix mypy checks here.
    #  See upstream approach: https://github.com/pallets/click/blob/main/src/click/decorators.py
    def wrapper(*args, **kwargs):  # type: ignore[no-untyped-def]
        return func(*args, **kwargs)

    return wrapper  # type: ignore[return-value]
