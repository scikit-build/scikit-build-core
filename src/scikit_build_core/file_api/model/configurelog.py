"""
.. seealso::
   - https://cmake.org/cmake/help/latest/manual/cmake-file-api.7.html#object-kind-configurelog
"""

import dataclasses
from typing import List, Union

from ..._compat.typing import TypeAlias
from ._common import APIVersion, ObjectKind

__all__ = ["ConfigureLog"]


def __dir__() -> List[str]:
    return __all__


# Note: version 1 does not exist, see note in upstream document
@dataclasses.dataclass(frozen=True)
class ConfigureLog_1_0(ObjectKind):
    """
    ..versionadded:: 3.26.0
    """

    kind = "configureLog"
    version = APIVersion(1, 0)
    # TODO: Further handle this?
    path: str
    eventKindNames: list[str]


ConfigureLog: TypeAlias = Union[ConfigureLog_1_0]
