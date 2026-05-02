from __future__ import annotations

import shutil
import typing

if typing.TYPE_CHECKING:
    from collections.abc import Iterator
    from pathlib import Path


__all__ = ["copy_force_include", "force_include_files"]


def __dir__() -> list[str]:
    return __all__


def force_include_files(source: Path, destination: Path) -> Iterator[tuple[Path, Path]]:
    if source.is_file():
        yield source, destination
        return

    if source.is_dir():
        for source_file in source.rglob("*"):
            if source_file.is_file():
                yield source_file, destination / source_file.relative_to(source)
        return

    msg = f"force-include source does not exist or is not a file/directory: {source}"
    raise FileNotFoundError(msg)


def copy_force_include(source: Path, destination: Path) -> None:
    for source_file, destination_file in force_include_files(source, destination):
        destination_file.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source_file, destination_file)
