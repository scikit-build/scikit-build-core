from __future__ import annotations

import contextlib
import os
from pathlib import Path
from typing import TYPE_CHECKING

import pathspec

from .._logging import logger
from ..format import pyproject_format

if TYPE_CHECKING:
    from collections.abc import Generator, Sequence

__all__ = ["each_unignored_file"]

EXCLUDE_LINES = [
    ".git",
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
    build_dir: str = "",
) -> Generator[Path, None, None]:
    """
    Runs through all non-ignored files. Must be run from the root directory.
    """
    global_exclude_lines = []
    for gi in [Path(".git/info/exclude"), Path(".gitignore")]:
        ignore_errs = [FileNotFoundError, NotADirectoryError]
        with contextlib.suppress(*ignore_errs), gi.open(encoding="utf-8") as f:
            global_exclude_lines += f.readlines()

    nested_excludes = {
        Path(dirpath): pathspec.GitIgnoreSpec.from_lines(
            (Path(dirpath) / filename).read_text(encoding="utf-8").splitlines()
        )
        for dirpath, _, filenames in os.walk(".")
        for filename in filenames
        if filename == ".gitignore" and dirpath != "."
    }

    exclude_build_dir = build_dir.format(**pyproject_format(dummy=True))

    exclude_lines = (
        [*EXCLUDE_LINES, exclude_build_dir] if exclude_build_dir else EXCLUDE_LINES
    )

    user_exclude_spec = pathspec.GitIgnoreSpec.from_lines(list(exclude))
    global_exclude_spec = pathspec.GitIgnoreSpec.from_lines(global_exclude_lines)
    builtin_exclude_spec = pathspec.GitIgnoreSpec.from_lines(exclude_lines)

    include_spec = pathspec.GitIgnoreSpec.from_lines(include)

    for dirstr, dirs, filenames in os.walk(str(starting_path), followlinks=True):
        dirpath = Path(dirstr)
        for dname in dirs:
            if not match_path(
                dirpath,
                dirpath / dname,
                include_spec,
                global_exclude_spec,
                builtin_exclude_spec,
                user_exclude_spec,
                nested_excludes,
                is_path=True,
            ):
                dirs.remove(dname)

        for fn in filenames:
            path = dirpath / fn
            if match_path(
                dirpath,
                path,
                include_spec,
                global_exclude_spec,
                builtin_exclude_spec,
                user_exclude_spec,
                nested_excludes,
                is_path=False,
            ):
                yield path


def match_path(
    dirpath: Path,
    p: Path,
    include_spec: pathspec.GitIgnoreSpec,
    global_exclude_spec: pathspec.GitIgnoreSpec,
    builtin_exclude_spec: pathspec.GitIgnoreSpec,
    user_exclude_spec: pathspec.GitIgnoreSpec,
    nested_excludes: dict[Path, pathspec.GitIgnoreSpec],
    *,
    is_path: bool,
) -> bool:
    ptype = "directory" if is_path else "file"

    # Always include something included
    if include_spec.match_file(p):
        logger.debug("Including {} {} because it is explicitly included.", ptype, p)
        return True

    # Always exclude something excluded
    if user_exclude_spec.match_file(p):
        logger.debug(
            "Excluding {} {} because it is explicitly excluded by the user.", ptype, p
        )
        return False

    # Ignore from global ignore
    if global_exclude_spec.match_file(p):
        logger.debug(
            "Excluding {} {} because it is explicitly excluded by the global ignore.",
            ptype,
            p,
        )
        return False

    # Ignore built-in patterns
    if builtin_exclude_spec.match_file(p):
        logger.debug(
            "Excluding {} {} because it is explicitly excluded by the built-in ignore.",
            ptype,
            p,
        )
        return False

    # Check relative ignores (Python 3.9's is_relative_to workaround)
    if any(
        nex.match_file(p.relative_to(np))
        for np, nex in nested_excludes.items()
        if dirpath == np or np in dirpath.parents
    ):
        logger.debug(
            "Excluding {} {} because it is explicitly excluded by nested ignore.",
            ptype,
            p,
        )
        return False

    logger.info(
        "Including {} {} because it exists (and isn't matched any other way).", ptype, p
    )
    return True
