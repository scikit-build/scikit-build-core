import dataclasses
from pathlib import Path

__all__ = ["APIVersion", "Paths"]


def __dir__() -> list[str]:
    return __all__


@dataclasses.dataclass(frozen=True)
class APIVersion:
    major: int
    minor: int


@dataclasses.dataclass(frozen=True)
class Paths:
    source: Path
    build: Path
