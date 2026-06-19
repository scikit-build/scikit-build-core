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

# Importable file extensions for the running interpreter, grouped in Python's
# loader precedence order: extension modules first, then source, then bytecode
# (see importlib.machinery._get_supported_file_loaders). EXTENSION_SUFFIXES is
# platform-specific (.cpython-313-x86_64-linux-gnu.so, .abi3.so, .so on Linux;
# .pyd on Windows), which matches the editable install resolving on the same
# platform it was built for.
_MODULE_SUFFIX_GROUPS = (
    tuple(importlib.machinery.EXTENSION_SUFFIXES),
    tuple(importlib.machinery.SOURCE_SUFFIXES),
    tuple(importlib.machinery.BYTECODE_SUFFIXES),
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

    Returns 0 for extension modules (``.so``, ``.pyd``, ``.abi3.so``, ...), 1
    for source (``.py``), 2 for bytecode (``.pyc``), matching the order Python's
    FileFinder tries them. Non-importable files (data/resource files, and
    versioned shared libraries such as ``_tango.so.10`` that alias the real
    ``_tango.so``) rank last, after every importable file (issue #1144).
    """
    name = path.name
    for rank, suffixes in enumerate(_MODULE_SUFFIX_GROUPS):
        if name.endswith(suffixes):
            return rank
    return len(_MODULE_SUFFIX_GROUPS)


def is_module(path: Path) -> bool:
    """
    True if ``path`` is an importable module file (``.py``, ``.pyc``, ``.so``,
    ``.pyd``, ``.abi3.so``, ...).

    Versioned shared libraries such as ``_tango.so.10`` or
    ``_tango.so.10.1.0.0`` are *not* importable -- they alias the real
    ``_tango.so`` -- so they return ``False`` and never shadow it when a module
    name is resolved (issue #1144).
    """
    return module_loader_rank(path) < len(_MODULE_SUFFIX_GROUPS)
