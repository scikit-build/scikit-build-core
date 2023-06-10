from __future__ import annotations

import contextlib
import os
from collections.abc import Generator, Sequence
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


def each_unignored_file(
    starting_path: Path,
    include: Sequence[str] = (),
    exclude: Sequence[str] = (),
) -> Generator[Path, None, None]:
    """
    Runs through all non-ignored files. Must be run from the root directory.
    """
    exclude_lines = EXCLUDE_LINES + list(exclude)
    gi = Path(".gitignore")
    with contextlib.suppress(FileNotFoundError), gi.open(encoding="utf-8") as f:
        exclude_lines += f.readlines()

    exclude_spec = pathspec.GitIgnoreSpec.from_lines(exclude_lines)
    include_spec = pathspec.GitIgnoreSpec.from_lines(include)

    for dirpath, _, filenames in os.walk(str(starting_path), followlinks=True):
        all_paths = (Path(dirpath) / fn for fn in filenames)
        paths = (
            p
            for p in all_paths
            if not exclude_spec.match_file(p) or include_spec.match_file(p)
        )
        yield from paths
