import dataclasses
from typing import List

from .common import APIVersion


@dataclasses.dataclass
class Property:
    name: str
    value: str


@dataclasses.dataclass
class Entry:
    name: str
    value: str
    type: str
    properties: List[Property]


@dataclasses.dataclass
class Cache:
    kind: str
    version: APIVersion
    entries: List[Entry]
