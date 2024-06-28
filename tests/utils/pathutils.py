from __future__ import annotations

import contextlib
import typing

if typing.TYPE_CHECKING:
    from collections.abc import Generator, Iterable
    from pathlib import Path


def contained(paths: Iterable[Path], rel: str) -> Generator[Path, None, None]:
    for p in paths:
        with contextlib.suppress(ValueError):
            yield p.relative_to(rel)
