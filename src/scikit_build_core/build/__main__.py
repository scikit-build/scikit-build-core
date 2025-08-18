import argparse
import json
from pathlib import Path
from typing import Literal

from .._compat import tomllib
from .._logging import rich_warning
from ..builder._load_provider import process_dynamic_metadata
from . import (
    get_requires_for_build_editable,
    get_requires_for_build_sdist,
    get_requires_for_build_wheel,
)


def main_project_table(_args: argparse.Namespace, /) -> None:
    """Get the full project table, including dynamic metadata."""
    with Path("pyproject.toml").open("rb") as f:
        pyproject = tomllib.load(f)

    project = pyproject.get("project", {})
    metadata = pyproject.get("tool", {}).get("scikit-build", {}).get("metadata", {})
    new_project = process_dynamic_metadata(project, metadata)
    print(json.dumps(new_project, indent=2))


def main_requires(args: argparse.Namespace, /) -> None:
    get_requires(args.mode)


def get_requires(mode: Literal["sdist", "wheel", "editable"]) -> None:
    """Get the build requirements."""

    with Path("pyproject.toml").open("rb") as f:
        pyproject = tomllib.load(f)

    requires = pyproject.get("build-system", {}).get("requires", [])
    backend = pyproject.get("build-system", {}).get("build-backend", "")
    if backend != "scikit_build_core.build":
        rich_warning("Might not be a scikit-build-core project.")
    if mode == "sdist":
        requires += get_requires_for_build_sdist({})
    elif mode == "wheel":
        requires += get_requires_for_build_wheel({})
    elif mode == "editable":
        requires += get_requires_for_build_editable({})
    print(json.dumps(sorted(set(requires)), indent=2))


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="python -m scikit_build_core.build",
        allow_abbrev=False,
        description="Build backend utilities.",
    )

    subparsers = parser.add_subparsers(required=True, help="Commands")
    requires = subparsers.add_parser(
        "requires",
        help="Get the build requirements",
        description="Includes the static build requirements, the dynamically generated ones, and dynamic-metadata ones.",
    )
    requires.set_defaults(func=main_requires)
    requires.add_argument(
        "--mode",
        choices=["sdist", "wheel", "editable"],
        default="wheel",
        help="The build mode to get the requirements for",
    )

    project_table = subparsers.add_parser(
        "project-table",
        help="Get the full project table, including dynamic metadata",
        description="Processes static and dynamic metadata without triggering the backend, only handles scikit-build-core's dynamic metadata.",
    )
    project_table.set_defaults(func=main_project_table)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
