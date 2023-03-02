from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path

from ._file_processor import each_unignored_file

__all__ = ["packages_to_file_mapping"]


def __dir__() -> list[str]:
    return __all__


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
