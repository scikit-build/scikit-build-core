"""
.. seealso::
   - https://cmake.org/cmake/help/latest/manual/cmake-file-api.7.html#object-kind-cache
"""

import dataclasses
from typing import List, Union

from ..._compat.typing import TypeAlias
from ._common import APIVersion, ObjectKind

__all__ = ["Cache"]


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


# Note: version 1 does not exist, see note in upstream document
@dataclasses.dataclass(frozen=True)
class Cache_2_0(ObjectKind):
    """
    ..versionadded:: 3.14.0
    """

    kind = "cache"
    version = APIVersion(2, 0)
    entries: List[Entry]


Cache: TypeAlias = Union[Cache_2_0]
