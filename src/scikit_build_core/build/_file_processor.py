from __future__ import annotations

import contextlib
import os
from pathlib import Path
from typing import TYPE_CHECKING, Literal

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
    *,
    mode: Literal["classic", "default", "manual"],
) -> Generator[Path, None, None]:
    """
    Runs through all non-ignored files. Must be run from the root directory.
    """
    global_exclude_lines = []
    if mode != "manual":
        for gi in [Path(".git/info/exclude"), Path(".gitignore")]:
            ignore_errs = [FileNotFoundError, NotADirectoryError]
            with contextlib.suppress(*ignore_errs), gi.open(encoding="utf-8") as f:
                global_exclude_lines += f.readlines()

    nested_excludes = (
        {}
        if mode == "manual"
        else {
            Path(dirpath): pathspec.GitIgnoreSpec.from_lines(
                (Path(dirpath) / filename).read_text(encoding="utf-8").splitlines()
            )
            for dirpath, _, filenames in os.walk(".")
            for filename in filenames
            if filename == ".gitignore" and dirpath != "."
        }
    )

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
        if mode != "classic":
            for dname in dirs:
                if not match_path(
                    dirpath / dname,
                    include_spec,
                    global_exclude_spec,
                    builtin_exclude_spec,
                    user_exclude_spec,
                    nested_excludes,
                    is_path=True,
                ):
                    # Check to see if any include rules start with this
                    dstr = (dirpath / dname).as_posix().strip("/") + "/"
                    if not any(p.lstrip("/").startswith(dstr) for p in include):
                        dirs.remove(dname)

        for fn in filenames:
            path = dirpath / fn
            if match_path(
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
    if (c := include_spec.check_file(p)).include:
        assert c.index is not None
        logger.debug(
            "Including {} {} because it is explicitly included by rule {!r}.",
            ptype,
            p,
            include_spec.patterns[c.index].pattern,
        )
        return True

    # Always exclude something excluded
    if (c := user_exclude_spec.check_file(p)).include:
        assert c.index is not None
        logger.debug(
            "Excluding {} {} because it is explicitly excluded by the user with {!r}.",
            ptype,
            p,
            user_exclude_spec.patterns[c.index].pattern,
        )
        return False

    # Ignore from global ignore
    if (c := global_exclude_spec.check_file(p)).include:
        assert c.index is not None
        logger.debug(
            "Excluding {} {} because it is explicitly excluded by the global ignore with {!r}.",
            ptype,
            p,
            global_exclude_spec.patterns[c.index].pattern,
        )
        return False

    # Ignore built-in patterns
    if (c := builtin_exclude_spec.check_file(p)).include:
        assert c.index is not None
        logger.debug(
            "Excluding {} {} because it is explicitly excluded by the built-in ignore with {!r}.",
            ptype,
            p,
            builtin_exclude_spec.patterns[c.index].pattern,
        )
        return False

    # Check relative ignores
    for np, nex in nested_excludes.items():
        if p.is_relative_to(np) and (c := nex.check_file(p.relative_to(np))).include:
            assert c.index is not None
            logger.debug(
                "Excluding {} {} because it is explicitly excluded by nested ignore with {!r}.",
                ptype,
                p,
                nex.patterns[c.index].pattern,
            )
            return False

    logger.debug(
        "Including {} {} because it exists (and isn't matched any other way).", ptype, p
    )
    return True
