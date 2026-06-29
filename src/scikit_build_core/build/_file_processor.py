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


def _dir_key(dirstr: str) -> tuple[int, int] | None:
    """
    Identify a directory by its (device, inode) pair so that symlink loops can
    be detected. Returns None if the directory can't be stat'd (it is then
    treated as not-yet-seen and handled normally).
    """
    try:
        st = Path(dirstr).stat()
    except OSError:
        return None
    return (st.st_dev, st.st_ino)


def each_unignored_file(
    starting_path: Path,
    include: Sequence[str] = (),
    exclude: Sequence[str] = (),
    build_dir: str = "",
    *,
    mode: Literal["classic", "default", "manual", "explicit"],
) -> Generator[Path, None, None]:
    """
    Runs through all non-ignored files. Must be run from the root directory.
    """
    # "manual" and "explicit" do not consult git ignore files at all.
    reads_gitignore = mode in {"classic", "default"}
    explicit = mode == "explicit"

    global_exclude_lines = []
    if reads_gitignore:
        for gi in [Path(".git/info/exclude"), Path(".gitignore")]:
            ignore_errs = [FileNotFoundError, NotADirectoryError]
            with contextlib.suppress(*ignore_errs), gi.open(encoding="utf-8") as f:
                global_exclude_lines += f.readlines()

    nested_excludes = (
        {
            Path(dirpath): pathspec.GitIgnoreSpec.from_lines(
                (Path(dirpath) / filename).read_text(encoding="utf-8").splitlines()
            )
            for dirpath, _, filenames in os.walk(".")
            for filename in filenames
            if filename == ".gitignore" and dirpath != "."
        }
        if reads_gitignore
        else {}
    )

    exclude_build_dir = build_dir.format(**pyproject_format(dummy=True))

    exclude_lines = (
        [*EXCLUDE_LINES, exclude_build_dir] if exclude_build_dir else EXCLUDE_LINES
    )

    user_exclude_spec = pathspec.GitIgnoreSpec.from_lines(list(exclude))
    global_exclude_spec = pathspec.GitIgnoreSpec.from_lines(global_exclude_lines)
    builtin_exclude_spec = pathspec.GitIgnoreSpec.from_lines(exclude_lines)

    include_spec = pathspec.GitIgnoreSpec.from_lines(include)

    # Map each visited directory to the set of (device, inode) keys of itself
    # and all of its ancestors along the walk path. A circular symlink
    # (e.g. pkg/sub/pkg -> ../../pkg) re-enters a directory that is one of its
    # own ancestors; pruning it stops os.walk from descending forever or
    # emitting duplicated, ever-deeper copies of the same files (#1101). A
    # symlink to an unrelated directory is not an ancestor of itself, so it is
    # still followed.
    ancestor_keys: dict[str, frozenset[tuple[int, int]]] = {}

    for dirstr, dirs, filenames in os.walk(str(starting_path), followlinks=True):
        dirpath = Path(dirstr)
        key = _dir_key(dirstr)
        # os.path.dirname keeps the exact string form os.walk uses for keys
        # (e.g. "" for the root), unlike Path.parent which maps it to ".".
        parent_keys = ancestor_keys.get(os.path.dirname(dirstr), frozenset())  # noqa: PTH120
        if key is not None and key in parent_keys:
            logger.debug(
                "Not descending into {} because it is an ancestor of itself "
                "(symlink loop).",
                dirpath,
            )
            dirs.clear()
            continue
        if key is not None:
            ancestor_keys[dirstr] = parent_keys | {key}
        if mode != "classic":
            for dname in list(dirs):
                if not match_path(
                    dirpath,
                    dirpath / dname,
                    include_spec,
                    global_exclude_spec,
                    builtin_exclude_spec,
                    user_exclude_spec,
                    nested_excludes,
                    is_path=True,
                    explicit=explicit,
                ):
                    # Only prune if no include pattern could match a file below
                    # this directory. A literal include deeper than the dir, or
                    # a glob include (e.g. ``pkg/**/*.py``) whose fixed prefix is
                    # this dir or an ancestor of it, must keep the dir walkable.
                    dstr = (dirpath / dname).as_posix().strip("/")
                    if not any(_include_may_match_below(p, dstr) for p in include):
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
                explicit=explicit,
            ):
                yield path


def _include_may_match_below(pattern: str, dirpath: str) -> bool:
    """
    Decide whether an include ``pattern`` could match any file beneath the
    directory ``dirpath`` (both POSIX, leading/trailing slashes stripped).

    The fixed (glob-free) leading portion of the pattern is compared against the
    directory. A glob like ``pkg/**/*.py`` has fixed prefix ``pkg`` and could
    match below ``pkg/sub``; a literal include like ``pkg/sub/file.py`` is
    deeper than ``pkg`` and must keep ``pkg`` walkable. Both cases reduce to the
    directory and the fixed prefix sharing an ancestor relationship.
    """
    cleaned = pattern.lstrip("/")
    prefix_parts: list[str] = []
    for part in cleaned.split("/"):
        # Stop at the first segment containing a glob metacharacter.
        if any(ch in part for ch in "*?[") or part == "**":
            break
        if part:
            prefix_parts.append(part)
    prefix = "/".join(prefix_parts)
    if not prefix:
        # A leading glob (e.g. ``**/*.py``) can match anywhere below the dir.
        return True
    dir_with_sep = f"{dirpath}/"
    prefix_with_sep = f"{prefix}/"
    # dir is an ancestor of (or equal to) the fixed prefix, or vice versa.
    return prefix_with_sep.startswith(dir_with_sep) or dir_with_sep.startswith(
        prefix_with_sep
    )


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
    explicit: bool = False,
) -> bool:
    ptype = "directory" if is_path else "file"

    # In "explicit" mode the set is purely include minus exclude: nothing is in
    # unless an include matches it, and exclude is applied after (so it wins over
    # include). git ignore files are not consulted (they are empty here anyway).
    if explicit:
        if (c := user_exclude_spec.check_file(p)).include:
            assert c.index is not None
            logger.debug(
                "Excluding {} {} because it is explicitly excluded by the user with {!r}.",
                ptype,
                p,
                user_exclude_spec.patterns[c.index].pattern,
            )
            return False
        if (c := include_spec.check_file(p)).include:
            assert c.index is not None
            logger.debug(
                "Including {} {} because it is explicitly included by rule {!r}.",
                ptype,
                p,
                include_spec.patterns[c.index].pattern,
            )
            return True
        logger.debug(
            "Excluding {} {} because no include rule opts it in (explicit mode).",
            ptype,
            p,
        )
        return False

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

    # Check relative ignores (Python 3.9's is_relative_to workaround)
    for np, nex in nested_excludes.items():
        if (dirpath == np or np in dirpath.parents) and (
            c := nex.check_file(p.relative_to(np))
        ).include:
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
