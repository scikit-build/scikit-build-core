from __future__ import annotations

import contextlib
import os
from collections.abc import Generator
from pathlib import Path

import pathspec

__all__: list[str] = ["each_unignored_file"]

EXCLUDE_LINES = [
    ".git/",
    ".tox/",
    ".nox/",
    ".egg-info/",
    "__pycache__/",
    "__pypackages__/",
    "*.pyc",
    "*.dist-info/",
]


def __dir__() -> list[str]:
    return __all__


def each_unignored_file(starting_path: Path) -> Generator[Path, None, None]:
    """
    Runs through all non-ignored files. Must be run from the root directory.
    """
    exclude_lines = EXCLUDE_LINES.copy()
    with contextlib.suppress(FileNotFoundError):
        with open(".gitignore", encoding="utf-8") as f:
            exclude_lines += f.readlines()

    exclude_spec = pathspec.GitIgnoreSpec.from_lines(exclude_lines)

    for dirpath, _, filenames in os.walk(str(starting_path)):
        paths = (Path(dirpath) / fn for fn in filenames)
        if exclude_spec is not None:
            paths = (p for p in paths if not exclude_spec.match_file(p))
        yield from paths
