import dataclasses
from pathlib import Path
from typing import List

__all__ = ["APIVersion", "Paths"]


def __dir__() -> List[str]:
    return __all__


@dataclasses.dataclass
class APIVersion:
    major: int
    minor: int


@dataclasses.dataclass
class Paths:
    source: Path
    build: Path
