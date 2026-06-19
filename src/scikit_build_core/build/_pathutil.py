from __future__ import annotations

import importlib.machinery
import os
from pathlib import Path
from typing import TYPE_CHECKING, Literal

import pathspec

from ._file_processor import each_unignored_file

if TYPE_CHECKING:
    from collections.abc import Generator, Mapping, Sequence

__all__ = [
    "is_module",
    "is_valid_module",
    "module_loader_rank",
    "packages_to_file_mapping",
    "path_to_module",
    "scantree",
]

# Importable file extensions for the running interpreter, in the exact order
# Python's FileFinder tries them: extension modules (most specific tag first,
# e.g. .cpython-313-x86_64-linux-gnu.so before .abi3.so before .so), then source
# (.py), then bytecode (.pyc) -- see
# importlib.machinery._get_supported_file_loaders. EXTENSION_SUFFIXES is
# platform- and interpreter-specific (.pyd on Windows), which matches an editable
# install resolving on the same interpreter it was built for.
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
    assert name, f"Empty name should be filtered by is_valid_module first, got {path}"
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


def is_valid_module(path: Path) -> bool:
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
    Where ``path`` sits in Python's import loader precedence.

    A file maps to the module name before its first ``.``; the rest is its
    suffix. The rank is that suffix's index in the ordered list of suffixes the
    interpreter's FileFinder tries (extension tags first, then ``.py``, then
    ``.pyc``), so when several files share a module name the one chosen matches
    what a real wheel import would load -- including between extension tags
    (``mod.cpython-313-...so`` beats ``mod.abi3.so`` beats ``mod.so``).
    Non-importable files -- data/resource files, and versioned shared libraries
    such as ``_tango.so.10`` whose ``.so.10`` is not a real suffix -- rank last
    (issue #1144).
    """
    _, dot, rest = path.name.partition(".")
    suffix = dot + rest
    try:
        return _MODULE_SUFFIXES.index(suffix)
    except ValueError:
        return len(_MODULE_SUFFIXES)


def is_module(path: Path) -> bool:
    """
    True if ``path`` is an importable module file for this interpreter.

    The file's suffix (everything after the first ``.`` in its name) must be one
    the interpreter imports: ``.py``, ``.pyc``, or an extension suffix such as
    ``.so``/``.pyd``/``.abi3.so``. Versioned shared libraries such as
    ``_tango.so.10`` are *not* importable -- they alias the real ``_tango.so`` --
    so they return ``False`` and never shadow it when a module name is resolved
    (issue #1144).
    """
    return module_loader_rank(path) < len(_MODULE_SUFFIXES)
