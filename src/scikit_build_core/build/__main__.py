from __future__ import annotations

__lazy_modules__ = {
    "argparse",
    "json",
    "scikit_build_core._logging",
    "scikit_build_core.builder",
    "scikit_build_core.builder._load_provider",
    "scikit_build_core.settings",
    "scikit_build_core.settings.__main__",
    "typing",
}

import argparse
import json
from typing import Literal, get_args

from scikit_build_core._logging import rich_warning
from scikit_build_core.build import (
    get_requires_for_build_editable,
    get_requires_for_build_sdist,
    get_requires_for_build_wheel,
)
from scikit_build_core.builder._load_provider import (
    BuildState,
    process_dynamic_metadata,
    process_legacy_dynamic_metadata,
)
from scikit_build_core.settings.__main__ import _load_pyproject


def main_project_table(args: argparse.Namespace, /) -> None:
    """Get the full project table, including dynamic metadata."""
    pyproject = _load_pyproject()

    project = pyproject.get("project", {})
    legacy = pyproject.get("tool", {}).get("scikit-build", {}).get("metadata", {})
    if legacy:
        project = process_legacy_dynamic_metadata(project, legacy)
    entries = pyproject.get("tool", {}).get("dynamic-metadata", [])
    if entries:
        project = process_dynamic_metadata(project, entries, build_state=args.state)
    print(json.dumps(project, indent=2))


def main_requires(args: argparse.Namespace, /) -> None:
    config_settings: dict[str, str | list[str]] = {}
    for item in args.config_settings:
        key, _, value = item.partition("=")
        if key not in config_settings:
            config_settings[key] = value
        elif isinstance(old := config_settings[key], list):
            old.append(value)
        else:
            config_settings[key] = [old, value]
    get_requires(args.mode, args.type, config_settings)


def get_requires(
    mode: Literal["sdist", "wheel", "editable"],
    kind: Literal["static", "dynamic", "both"] = "both",
    config_settings: dict[str, str | list[str]] | None = None,
) -> None:
    """Get the build requirements."""

    pyproject = _load_pyproject()

    requires: list[str] = []
    if kind != "dynamic":
        requires += pyproject.get("build-system", {}).get("requires", [])
    if kind != "static":
        backend = pyproject.get("build-system", {}).get("build-backend", "")
        if backend != "scikit_build_core.build":
            rich_warning("Might not be a scikit-build-core project.")
        if mode == "sdist":
            requires += get_requires_for_build_sdist(config_settings)
        elif mode == "wheel":
            requires += get_requires_for_build_wheel(config_settings)
        elif mode == "editable":
            requires += get_requires_for_build_editable(config_settings)
    print(json.dumps(sorted(set(requires)), indent=2))


def populate_parser(parser: argparse.ArgumentParser, /) -> None:
    """Add the ``build`` subcommands to an existing parser."""
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
    requires.add_argument(
        "--type",
        choices=["static", "dynamic", "both"],
        default="both",
        help="Static (build-system.requires), dynamic (from the backend hook), or both",
    )
    requires.add_argument(
        "-C",
        "--config-setting",
        dest="config_settings",
        action="append",
        default=[],
        metavar="KEY=VALUE",
        help="A config-setting passed to the backend hook, can be repeated",
    )

    project_table = subparsers.add_parser(
        "project-table",
        help="Get the full project table, including dynamic metadata",
        description="Processes static and dynamic metadata without triggering the backend, only handles scikit-build-core's dynamic metadata.",
    )
    project_table.set_defaults(func=main_project_table)
    project_table.add_argument(
        "--state",
        choices=get_args(BuildState),
        default="metadata_wheel",
        help="The build state reported to [[tool.dynamic-metadata]] providers",
    )


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="python -m scikit_build_core.build",
        allow_abbrev=False,
        description="Build backend utilities.",
    )
    populate_parser(parser)
    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
