from __future__ import annotations

import sys
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import argparse

__all__ = ["stateless_query"]


def __dir__() -> list[str]:
    return __all__


def stateless_query(build_dir: Path) -> Path:
    api_dir = build_dir / ".cmake/api/v1"
    query = api_dir.joinpath("query")
    query.mkdir(parents=True, exist_ok=True)

    query.joinpath("codemodel-v2").touch()
    query.joinpath("cache-v2").touch()
    query.joinpath("cmakeFiles-v1").touch()
    query.joinpath("toolchains-v1").touch()
    return api_dir / "reply"


def main_query(args: argparse.Namespace, /) -> None:
    result = stateless_query(args.build_dir)
    sys.stdout.write(f"{result}\n")


def populate_parser(parser: argparse.ArgumentParser, /) -> None:
    """Add the ``query`` argument to an existing parser."""
    parser.add_argument("build_dir", type=Path, help="Path to the build directory")
    parser.set_defaults(func=main_query)


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(
        prog="python -m scikit_build_core.file_api.query",
        allow_abbrev=False,
        description="Write a stateless query to a build directory",
    )
    populate_parser(parser)
    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
