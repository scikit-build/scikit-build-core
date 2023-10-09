from __future__ import annotations

import click

from .main import skbuild

__all__: list[str] = ["dynamic_metadata"]


def __dir__() -> list[str]:
    return __all__


@skbuild.command()
@click.pass_context
def dynamic_metadata(ctx: click.Context) -> None:  # noqa: ARG001
    """
    Get the generated dynamic metadata
    """
    # TODO: Add specific implementations
