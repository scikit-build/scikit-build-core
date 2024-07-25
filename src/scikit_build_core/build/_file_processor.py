from __future__ import annotations

import contextlib
import os
from pathlib import Path
from typing import TYPE_CHECKING

import pathspec

if TYPE_CHECKING:
    from collections.abc import Generator, Sequence

__all__ = ["each_unignored_file"]

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

    for gi in [Path(".git/info/exclude"), Path(".gitignore")]:
        with contextlib.suppress(FileNotFoundError), gi.open(encoding="utf-8") as f:
            exclude_lines += f.readlines()

    nested_excludes = {
        p.parent: pathspec.GitIgnoreSpec.from_lines(p.read_text().splitlines())
        for p in Path().rglob("**/.gitignore")
        if p != Path(".gitignore")
    }

    exclude_spec = pathspec.GitIgnoreSpec.from_lines(exclude_lines)
    include_spec = pathspec.GitIgnoreSpec.from_lines(include)

    for dirstr, _, filenames in os.walk(str(starting_path), followlinks=True):
        dirpath = Path(dirstr)
        all_paths = (dirpath / fn for fn in filenames)
        for p in all_paths:
            # Always include something included
            if include_spec.match_file(p):
                yield p

            # Ignore from global ignore
            if exclude_spec.match_file(p):
                continue

            # Check relative ignores (Python 3.9's is_relative_to workaround)
            if any(
                nex.match_file(p.relative_to(np))
                for np, nex in nested_excludes.items()
                if dirpath == np or np in dirpath.parents
            ):
                continue

            yield p
