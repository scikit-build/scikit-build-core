from __future__ import annotations

import click

from .. import __version__

__all__ = ["skbuild"]


def __dir__() -> list[str]:
    return __all__


@click.group("skbuild")
@click.version_option(__version__)
@click.pass_context
def skbuild(ctx: click.Context) -> None:  # noqa: ARG001
    """
    scikit-build Main CLI interface
    """
    # TODO: Add specific implementations
