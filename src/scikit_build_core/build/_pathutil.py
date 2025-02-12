from __future__ import annotations

import os
from pathlib import Path
from typing import TYPE_CHECKING

import pathspec

from ._file_processor import each_unignored_file

if TYPE_CHECKING:
    from collections.abc import Generator, Mapping, Sequence

__all__ = ["is_valid_module", "packages_to_file_mapping", "path_to_module", "scantree"]


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
        ):
            rel_path = filepath.relative_to(source_dir)
            target_path = platlib_dir / package_dir / rel_path
            if not exclude_spec.match_file(rel_path) and not target_path.is_file():
                mapping[str(filepath)] = str(target_path)

    return mapping


def is_valid_module(path: Path) -> bool:
    parts = path.parts
    return (
        all(p.isidentifier() for p in parts[:-1])
        and parts[-1].split(".", 1)[0].isidentifier()
    )
