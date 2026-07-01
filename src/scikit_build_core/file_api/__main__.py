from __future__ import annotations

__lazy_modules__ = {"argparse"}

import argparse

from . import query, reply

__all__ = ["main"]


def __dir__() -> list[str]:
    return __all__


def populate_parser(parser: argparse.ArgumentParser, /) -> None:
    """Add the ``file-api`` subcommands to an existing parser."""
    subparsers = parser.add_subparsers(required=True, help="Commands")
    query_parser = subparsers.add_parser(
        "query",
        help="Write a stateless query to a build directory",
        description="Write a stateless query to a build directory.",
        allow_abbrev=False,
    )
    query.populate_parser(query_parser)
    reply_parser = subparsers.add_parser(
        "reply",
        help="Read a query written out to a build directory",
        description="Read a query written out to a build directory.",
        allow_abbrev=False,
    )
    reply.populate_parser(reply_parser)


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="python -m scikit_build_core.file_api",
        allow_abbrev=False,
        description="CMake file API utilities.",
    )
    populate_parser(parser)
    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
