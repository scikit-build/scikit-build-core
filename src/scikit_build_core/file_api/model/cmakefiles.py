"""
.. seealso::
   - https://cmake.org/cmake/help/latest/manual/cmake-file-api.7.html#object-kind-cmakefiles
"""

import dataclasses
from dataclasses import field
from pathlib import Path
from typing import List, Union

from ..._compat.typing import TypeAlias
from ._common import APIVersion, ObjectKind, Paths

__all__ = ["CMakeFiles"]


def __dir__() -> List[str]:
    return __all__


@dataclasses.dataclass(frozen=True)
class Input:
    path: Path
    isGenerated: bool = False
    isExternal: bool = False
    isCMake: bool = False


@dataclasses.dataclass(frozen=True)
class GlobsDependent:
    expression: str
    recurse: bool = False
    listDirectories: bool = False
    followSymlinks: bool = False
    relative: Union[str, None] = None
    paths: list[str] = field(default_factory=list)


@dataclasses.dataclass(frozen=True)
class CMakeFiles_1_0(ObjectKind):
    """
    ..versionadded:: 3.14.0
    """

    kind = "cmakeFiles"
    version = APIVersion(1, 0)
    paths: Paths
    inputs: List[Input]


@dataclasses.dataclass(frozen=True)
class CMakeFiles_1_1(CMakeFiles_1_0):
    """
    ..versionadded:: 3.30.0
    """

    version = APIVersion(1, 0)

    globsDependent: List[GlobsDependent] = field(default_factory=list)


CMakeFiles: TypeAlias = Union[CMakeFiles_1_0, CMakeFiles_1_1]
