from __future__ import annotations

import importlib.machinery
import os
from pathlib import Path, PurePosixPath
from typing import TYPE_CHECKING, Literal

import pathspec

from .._logging import logger
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
    mode: Literal["classic", "default", "manual"],
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
    if ".." in dest:
        msg = f"Wheel destination must not contain '..', got {dest!r}"
        raise AssertionError(msg)
    if dest.startswith("/"):
        if not experimental:
            msg = "Experimental features must be enabled to use absolute paths (a leading '/') in a wheel destination"
            raise AssertionError(msg)
        tree, _, rest = dest[1:].partition("/")
        if tree not in wheel_dirs:
            msg = f"Must target a valid wheel directory, not {tree!r}"
            raise AssertionError(msg)
        return wheel_dirs[tree], rest
    return wheel_dirs[targetlib], dest


def iter_force_include(
    source: str, dest: str, base: Path
) -> Iterator[tuple[Path, Path]]:
    """
    Yield ``(source_file, target_path)`` pairs for a force-include entry.

    ``source`` may be a file or a directory (relative to the project root, may
    point outside it, with ``~`` expanded). A file yields a single pair mapped to
    ``base / dest``; a directory is walked recursively (skipping VCS and
    ``__pycache__`` junk) with each file mapped under ``base / dest``. A source
    that does not exist yields nothing -- it is assumed to already be present at
    the destination (e.g. when building a wheel from an SDist).

    ``dest`` must be a relative path within ``base``; an absolute path or one
    with ``..`` components (which would escape ``base``) is rejected. Wheel-tree
    selection (a leading ``/``) is handled earlier by :func:`resolve_wheel_tree`.
    """
    dest_path = PurePosixPath(dest)
    if dest_path.is_absolute() or ".." in dest_path.parts:
        msg = (
            f"Force-include destination {dest!r} for {source!r} must be a "
            "relative path without '..'"
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
        logger.debug("Force-include source {!r} not found, skipping", source)


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
