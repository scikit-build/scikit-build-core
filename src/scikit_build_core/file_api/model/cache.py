import dataclasses
from typing import List

from .common import APIVersion

__all__ = ["Cache", "Entry", "Property"]


def __dir__() -> List[str]:
    return __all__


@dataclasses.dataclass(frozen=True)
class Property:
    name: str
    value: str


@dataclasses.dataclass(frozen=True)
class Entry:
    name: str
    value: str
    type: str
    properties: List[Property]


@dataclasses.dataclass(frozen=True)
class Cache:
    kind: str
    version: APIVersion
    entries: List[Entry]
