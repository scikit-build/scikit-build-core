from __future__ import annotations

from typing import TYPE_CHECKING

import click

from .main import skbuild
from .utils import _build_dir

if TYPE_CHECKING:
    from pathlib import Path

__all__: list[str] = ["build"]


def __dir__() -> list[str]:
    return __all__


@skbuild.command()
@_build_dir
@click.pass_context
def build(ctx: click.Context, build_dir: Path) -> None:  # noqa: ARG001
    """
    Run cmake build step
    """
    # TODO: Add specific implementations
