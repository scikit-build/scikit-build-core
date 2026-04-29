import dataclasses

from .common import APIVersion

__all__ = ["Cache", "Entry", "Property"]


def __dir__() -> list[str]:
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
    properties: list[Property]


@dataclasses.dataclass(frozen=True)
class Cache:
    kind: str
    version: APIVersion
    entries: list[Entry]
