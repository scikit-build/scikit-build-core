from __future__ import annotations

import os
from collections.abc import Generator, Sequence
from pathlib import Path

from ._file_processor import each_unignored_file

__all__ = ["scantree", "path_to_module", "packages_to_file_mapping"]


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
    path = path.with_name(path.name.split(".", 1)[0])
    if path.name == "__init__":
        path = path.parent
    return ".".join(path.parts)


def packages_to_file_mapping(
    *,
    packages: Sequence[str],
    platlib_dir: Path,
    include: Sequence[str],
    exclude: Sequence[str],
) -> dict[str, str]:
    mapping = {}
    for package in packages:
        source_package = Path(package)
        base_path = source_package.parent
        for filepath in each_unignored_file(
            source_package,
            include=include,
            exclude=exclude,
        ):
            package_dir = platlib_dir / filepath.relative_to(base_path)
            if not package_dir.is_file():
                mapping[str(filepath)] = str(package_dir)

    return mapping
