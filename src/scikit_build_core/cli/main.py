from __future__ import annotations

import pathlib
import sys

import click

from .. import __version__
from .._compat.importlib import metadata

__all__ = ["skbuild"]


def __dir__() -> list[str]:
    return __all__


@click.group("skbuild")
@click.version_option(__version__)
@click.option(
    "--root",
    "-r",
    type=click.Path(
        exists=True,
        file_okay=False,
        dir_okay=True,
        writable=True,
        path_type=pathlib.Path,
    ),
    help="Path to the python project's root",
)
@click.pass_context
def skbuild(ctx: click.Context, root: pathlib.Path) -> None:  # noqa: ARG001
    """
    scikit-build Main CLI interface
    """
    # TODO: Add specific implementations


# Add all plugin commands. Native subcommands are loaded in the package's __init__
for ep in metadata.entry_points(group="skbuild.commands"):
    try:
        # Entry point can either point to a whole module or the decorated command
        if not ep.attr:
            # If it's a module, just load the module. It should have the necessary `sbuild.command` interface
            ep.load()
        else:
            # Otherwise assume it is a decorated command that needs to be loaded manually
            skbuild.add_command(ep.load())
    except Exception as err:  # noqa: PERF203
        # TODO: the print should go through the click logging interface
        print(f"Could not load cli plugin: {ep}\n{err}", file=sys.stderr)  # noqa: T201
