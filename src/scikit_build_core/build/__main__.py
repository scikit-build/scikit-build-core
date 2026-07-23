from __future__ import annotations

__lazy_modules__ = {
    "argparse",
    "json",
    "pathlib",
    "scikit_build_core._compat",
    "scikit_build_core._logging",
    "scikit_build_core.builder",
    "scikit_build_core.builder._load_provider",
    "scikit_build_core.settings",
    "scikit_build_core.settings.config_settings",
    "scikit_build_core.settings.documentation",
    "scikit_build_core.settings.skbuild_model",
    "typing",
}

import argparse
import json
from pathlib import Path
from typing import Any, Literal, get_args

from scikit_build_core._compat import tomllib
from scikit_build_core._logging import rich_error, rich_print, rich_warning
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
from scikit_build_core.settings.config_settings import load_declarations
from scikit_build_core.settings.documentation import mk_docs
from scikit_build_core.settings.skbuild_model import ScikitBuildSettings


def _load_pyproject() -> dict[str, Any]:
    """Read ``pyproject.toml`` from the current directory, erroring out clearly if missing."""
    path = Path("pyproject.toml")
    if not path.is_file():
        rich_error(
            "No {bold}pyproject.toml{normal} found in the current directory; run this from the root of a project."
        )
    with path.open("rb") as f:
        return tomllib.load(f)


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
    get_requires(args.mode)


def get_requires(mode: Literal["sdist", "wheel", "editable"]) -> None:
    """Get the build requirements."""

    pyproject = _load_pyproject()

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


def _brace_escape(text: str) -> str:
    """Escape braces so ``rich_print`` doesn't treat them as format fields."""
    return text.replace("{", "{{").replace("}", "}}")


def main_config_settings(_args: argparse.Namespace, /) -> None:
    """List the config-settings supported when building the project."""
    pyproject = _load_pyproject()
    backend = pyproject.get("build-system", {}).get("build-backend", "")
    if backend != "scikit_build_core.build":
        rich_warning("Might not be a scikit-build-core project.")

    rich_print(
        "{blue}Config-settings supported when building this project"
        " (pass with {bold}-C{normal}{blue}name=value):"
    )
    rich_print()

    decls = load_declarations(
        pyproject.get("tool", {}).get("scikit-build", {}).get("config-setting", {})
    )
    if decls:
        rich_print(
            "{bold}Project config-settings{normal} (tool.scikit-build.config-setting):"
        )
        width = max(len(name) for name in decls)
        for name, decl in decls.items():
            notes: list[str] = [decl.type]
            if decl.env is not None:
                notes.append(f"env: {decl.env}")
            if decl.default is not None:
                notes.append(f"default: {json.dumps(decl.default)}")
            rich_print(
                f"  {{green}}{name:{width}}{{default}}  {_brace_escape(decl.help)}"
                f" {{yellow}}[{_brace_escape(', '.join(notes))}]"
            )
        rich_print()

    items = [
        item
        for item in mk_docs(ScikitBuildSettings)
        if not item.deprecated and item.flat_expressible()
    ]
    rich_print(
        "{bold}Built-in config-settings{normal} (a 'skbuild.' prefix also works):"
    )
    width = max(len(item.name) for item in items)
    for item in items:
        summary = item.docs.split("\n", maxsplit=1)[0]
        rich_print(
            f"  {{green}}{item.name:{width}}{{default}}  {_brace_escape(summary)}"
            f" {{yellow}}[{_brace_escape(item.type)}]"
        )


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

    config_settings = subparsers.add_parser(
        "config-settings",
        help="List the config-settings supported when building this project",
        description="Lists the built-in scikit-build-core settings and any config-settings the project declares in tool.scikit-build.config-setting.",
    )
    config_settings.set_defaults(func=main_config_settings)


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
