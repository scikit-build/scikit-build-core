import dataclasses
from functools import total_ordering
from pathlib import Path
from typing import List

__all__ = ["APIVersion", "Paths"]


def __dir__() -> List[str]:
    return __all__


@total_ordering
@dataclasses.dataclass(frozen=True, eq=True)
class APIVersion:
    major: int
    minor: int

    def __gt__(self, other: "APIVersion") -> bool:
        if not isinstance(other, APIVersion):
            raise NotImplementedError
        if self.major > other.major:
            return True
        if self.major < other.major:
            return False
        if self.minor > other.minor:
            return True
        if self.minor < other.minor:
            return False
        return False


@dataclasses.dataclass(frozen=True)
class Paths:
    source: Path
    build: Path
