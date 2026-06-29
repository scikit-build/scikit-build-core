from __future__ import annotations

import importlib.machinery
import os
from pathlib import Path, PurePosixPath, PureWindowsPath
from typing import TYPE_CHECKING, Literal

import pathspec

from ._file_processor import EXCLUDE_LINES, each_unignored_file

if TYPE_CHECKING:
    from collections.abc import Generator, Iterator, Mapping, Sequence

__all__ = [
    "is_module",
    "is_trackable",
    "iter_force_include",
    "module_loader_rank",
    "packages_to_file_mapping",
    "path_to_module",
    "resolve_from_sdist_force_include",
    "resolve_wheel_tree",
    "scantree",
]

# Importable suffixes for this interpreter, in order.
_MODULE_SUFFIXES = (
    *importlib.machinery.EXTENSION_SUFFIXES,
    *importlib.machinery.SOURCE_SUFFIXES,
    *importlib.machinery.BYTECODE_SUFFIXES,
)


def __dir__() -> list[str]:
    return __all__


def scantree(path: Path) -> Generator[Path, None, None]:
    """Recursively yield Path objects for given directory."""
    for entry in os.scandir(path):
        if entry.is_dir(follow_symlinks=False):
            yield from scantree(Path(entry))
        else:
            yield Path(entry)


def path_to_module(path: Path) -> str:
    name, _, _ = path.name.partition(".")
    assert name, f"Empty name should be filtered by is_trackable first, got {path}"
    path = path.with_name(name)
    if path.name == "__init__":
        path = path.parent
    return ".".join(path.parts)


def packages_to_file_mapping(
    *,
    packages: Mapping[str, str],
    platlib_dir: Path,
    include: Sequence[str],
    src_exclude: Sequence[str],
    target_exclude: Sequence[str],
    build_dir: str,
    mode: Literal["classic", "default", "manual", "explicit"],
) -> dict[str, str]:
    """
    This will output a mapping of source files to target files.
    """
    mapping = {}
    exclude_spec = pathspec.GitIgnoreSpec.from_lines(target_exclude)
    for package_str, source_str in packages.items():
        package_dir = Path(package_str)
        source_dir = Path(source_str)

        for filepath in each_unignored_file(
            source_dir,
            include=include,
            exclude=src_exclude,
            build_dir=build_dir,
            mode=mode,
        ):
            rel_path = filepath.relative_to(source_dir)
            target_path = platlib_dir / package_dir / rel_path
            if not exclude_spec.match_file(rel_path) and not target_path.is_file():
                mapping[str(filepath)] = str(target_path)

    return mapping


def resolve_wheel_tree(
    dest: str,
    *,
    wheel_dirs: Mapping[str, Path],
    targetlib: str,
    experimental: bool,
) -> tuple[Path, str]:
    """
    Resolve a wheel destination into a ``(base_dir, relative_dest)`` pair.

    A plain ``dest`` is relative to the target lib (platlib/purelib). A leading
    ``/`` selects a wheel tree (``/data``, ``/scripts``, ``/headers``,
    ``/platlib``, ``/metadata``, ...) and requires experimental features, since
    this gives access one level above the platlib root.
    """
    # Reject a '..' parent-directory component (the traversal risk), but allow
    # adjacent dots inside a normal filename like 'data..json'.
    if ".." in PurePosixPath(dest).parts:
        msg = f"Wheel destination must not contain a '..' path component, got {dest!r}"
        raise AssertionError(msg)
    if dest.startswith("/"):
        if not experimental:
            msg = "Experimental features must be enabled to use absolute paths (a leading '/') in a wheel destination"
            raise AssertionError(msg)
        tree, _, rest = dest[1:].partition("/")
        # platlib/purelib both name the target lib; map either to whichever this
        # wheel actually has (pure wheels are keyed by purelib, not platlib).
        if tree in {"platlib", "purelib"}:
            tree = targetlib
        if tree not in wheel_dirs:
            msg = f"Must target a valid wheel directory, not {tree!r}"
            raise AssertionError(msg)
        return wheel_dirs[tree], rest
    return wheel_dirs[targetlib], dest


def resolve_from_sdist_force_include(
    source: str, sdist_force_include: Mapping[str, str]
) -> str:
    """
    Resolve a ``wheel.force-include`` source through the ``sdist.force-include`` map.

    A common pattern vendors an external file into the sdist with
    ``sdist.force-include`` and then ships that output via ``wheel.force-include``
    (e.g. source ``mypackage/data.json`` for both). The file only exists on disk
    when building from an unpacked sdist; a source-tree or editable build never
    materialized it. In that case, map ``source`` back through
    ``sdist_force_include`` (``{sdist_source: sdist_dest}``) to the original
    source so the file is found either way.

    An on-disk file always wins: if ``source`` exists it is returned unchanged.
    Otherwise the longest ``sdist_dest`` that equals ``source`` or is a parent
    directory of it wins, and its ``sdist_source`` (plus any remainder) is
    returned -- ``~`` / ``..`` are left intact for :func:`iter_force_include` to
    expand. With no match, ``source`` is returned unchanged and the caller raises
    :class:`FileNotFoundError`.
    """
    if Path(source).expanduser().exists():
        return source
    src = PurePosixPath(source)
    best_depth = -1
    resolved = source
    for sdist_source, sdist_dest in sdist_force_include.items():
        dest = PurePosixPath(sdist_dest)
        if src != dest and dest not in src.parents:
            continue
        depth = len(dest.parts)
        if depth > best_depth:
            best_depth = depth
            resolved = str(PurePosixPath(sdist_source) / src.relative_to(dest))
    return resolved


def iter_force_include(
    source: str, dest: str, base: Path
) -> Iterator[tuple[Path, Path]]:
    """
    Yield ``(source_file, target_path)`` pairs for a force-include entry.

    ``source`` may be a file or a directory (relative to the project root, may
    point outside it or be absolute, with ``~`` expanded). A file yields a single
    pair mapped to ``base / dest``; a directory is walked recursively (skipping
    VCS and ``__pycache__`` junk) with each file mapped under ``base / dest``.

    A missing source raises :class:`FileNotFoundError`.

    ``dest`` must be a relative path within ``base``; anything that could escape
    it is rejected -- an absolute path, ``..`` components, a backslash, or a
    Windows drive (e.g. ``C:/x``), which would otherwise escape on Windows where
    ``base / dest`` treats those as filesystem syntax. Wheel-tree selection (a
    leading ``/``) is handled earlier by :func:`resolve_wheel_tree`.
    """
    posix_dest = PurePosixPath(dest)
    if (
        "\\" in dest
        or PureWindowsPath(dest).drive
        or posix_dest.is_absolute()
        or ".." in posix_dest.parts
    ):
        msg = (
            f"Force-include destination {dest!r} for {source!r} must be a "
            "relative path without '..', a drive, or backslashes"
        )
        raise AssertionError(msg)
    src = Path(source).expanduser()
    if src.is_file():
        yield src, base / dest
    elif src.is_dir():
        exclude_spec = pathspec.GitIgnoreSpec.from_lines(EXCLUDE_LINES)
        for filepath in scantree(src):
            rel_path = filepath.relative_to(src)
            if not exclude_spec.match_file(rel_path):
                yield filepath, base / dest / rel_path
    else:
        msg = f"Force-include source {source!r} not found"
        raise FileNotFoundError(msg)


def is_trackable(path: Path) -> bool:
    """
    True if ``path`` should be tracked in an editable install.

    This is intentionally broad: it accepts data/resource files (``.txt``,
    ``.pyx``, ``.pxd``, ...) as well as importable modules, so that the editable
    redirect registers their directories and ``importlib.resources`` can find
    them. Use :func:`is_module` to tell whether a tracked file is importable.
    """
    parts = path.parts
    return (
        all(p.isidentifier() for p in parts[:-1])
        and parts[-1].partition(".")[0].isidentifier()
    )


def module_loader_rank(path: Path) -> int:
    """
    Index of ``path``'s suffix in Python's import loader precedence.

    A file maps to the module name before its first ``.``; the rest is its
    suffix. Ranking by that suffix's position in the FileFinder order (extension
    tags first, then ``.py``, then ``.pyc``) makes a shared module name resolve
    to the same file a real wheel import would load -- ``mod.cpython-313-...so``
    beats ``mod.abi3.so`` beats ``mod.so`` beats ``mod.py``. Non-importable files
    -- data and versioned shared libraries like ``_tango.so.10`` -- rank last
    (#1144).
    """
    _, dot, rest = path.name.partition(".")
    suffix = dot + rest
    try:
        return _MODULE_SUFFIXES.index(suffix)
    except ValueError:
        return len(_MODULE_SUFFIXES)


def is_module(path: Path) -> bool:
    """
    True if ``path``'s suffix is one this interpreter imports (``.py``, ``.pyc``,
    or an extension suffix like ``.so``/``.pyd``/``.abi3.so``).

    Versioned shared libraries like ``_tango.so.10`` alias the real ``_tango.so``
    and are not importable, so they never shadow it (#1144).
    """
    return module_loader_rank(path) < len(_MODULE_SUFFIXES)
