from __future__ import annotations

import argparse

from ._logging import rich_print

TYPE_CHECKING = False
if TYPE_CHECKING:
    from collections.abc import Sequence

__all__ = ["main"]


def __dir__() -> list[str]:
    return __all__


def main_info(_args: argparse.Namespace | None = None, /) -> None:
    rich_print("{blue}The scikit-build-core CLI provides the following commands:")
    rich_print("  scikit-build build requires        {green}Get the build requirements")
    rich_print(
        "  scikit-build build project-table   {green}Get the project table (with dynamic metadata)"
    )
    rich_print("  scikit-build builder               {green}Info about the system")
    rich_print(
        "  scikit-build builder wheel-tag     {green}Info about the computed wheel tag"
    )
    rich_print("  scikit-build builder sysconfig     {green}Info from sysconfig")
    rich_print("  scikit-build file-api query        {green}Request CMake file API")
    rich_print("  scikit-build file-api reply        {green}Process CMake file API")
    rich_print("  scikit-build init                  {green}Generate a starter project")
    rich_print()


def main(argv: Sequence[str] | None = None) -> None:
    from .build import __main__ as build_main
    from .builder import __main__ as builder_main
    from .file_api import __main__ as file_api_main
    from .init import __main__ as init_main

    parser = argparse.ArgumentParser(
        prog="scikit-build",
        allow_abbrev=False,
        description="scikit-build-core command line interface.",
    )
    parser.set_defaults(func=main_info)
    subparsers = parser.add_subparsers(help="Commands")

    build_parser = subparsers.add_parser(
        "build",
        help="Build backend utilities",
        description="Build backend utilities.",
        allow_abbrev=False,
    )
    build_main.populate_parser(build_parser)

    builder_parser = subparsers.add_parser(
        "builder",
        help="Info about the system and build environment",
        description="Info about the system and build environment.",
        allow_abbrev=False,
    )
    builder_main.populate_parser(builder_parser)

    file_api_parser = subparsers.add_parser(
        "file-api",
        help="CMake file API utilities",
        description="CMake file API utilities.",
        allow_abbrev=False,
    )
    file_api_main.populate_parser(file_api_parser)

    init_parser = subparsers.add_parser(
        "init",
        help="Generate a starter project",
        description="Generate a minimal CMake + scikit-build-core starter project.",
        allow_abbrev=False,
    )
    init_main.populate_parser(init_parser)

    args = parser.parse_args(argv)
    args.func(args)


if __name__ == "__main__":
    main()
