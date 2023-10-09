from __future__ import annotations

import click

from .main import skbuild

__all__: list[str] = ["metadata"]


def __dir__() -> list[str]:
    return __all__


@skbuild.command()
@click.pass_context
def metadata(ctx: click.Context) -> None:  # noqa: ARG001
    """
    Write out the project's metadata
    """
    # TODO: Add specific implementations
