from __future__ import annotations

from pathlib import Path


def stateless_query(build_dir: Path) -> None:
    api_dir = build_dir / ".cmake/api/v1"
    query = api_dir.joinpath("query")
    query.mkdir(parents=True, exist_ok=True)

    query.joinpath("codemodel-v2").touch()
    query.joinpath("cache-v2").touch()
    query.joinpath("cmakeFiles-v1").touch()
    query.joinpath("toolchains-v1").touch()


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("build_dir", type=Path, help="Path to the build directory")
    args = parser.parse_args()

    stateless_query(args.build_dir)
