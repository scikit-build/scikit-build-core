"""
.. seealso::
   - https://cmake.org/cmake/help/latest/manual/cmake-file-api.7.html#object-kind-toolchains
"""

import dataclasses
from pathlib import Path
from typing import List, Optional, Union

from ..._compat.typing import TypeAlias
from ._common import APIVersion, ObjectKind

__all__ = ["Toolchains"]


def __dir__() -> List[str]:
    return __all__


@dataclasses.dataclass(frozen=True)
class Implicit:
    includeDirectories: List[Path] = dataclasses.field(default_factory=list)
    linkDirectories: List[Path] = dataclasses.field(default_factory=list)
    linkFrameworkDirectories: List[Path] = dataclasses.field(default_factory=list)
    linkLibraries: List[Path] = dataclasses.field(default_factory=list)


@dataclasses.dataclass(frozen=True)
class Compiler_1_0:
    implicit: Implicit
    path: Optional[Path] = None
    id: Optional[str] = None
    version: Optional[str] = None
    target: Optional[str] = None


@dataclasses.dataclass(frozen=True)
class Toolchain_1_0:
    """
    ..versionadded:: 3.20.0
    """

    language: str  # Unique, since CMake supports one toolchain per language
    compiler: Compiler_1_0
    sourceFileExtensions: List[str] = dataclasses.field(default_factory=list)


@dataclasses.dataclass(frozen=True)
class Toolchains_1_0(ObjectKind):
    """
    ..versionadded:: 3.20.0
    """

    kind = "toolchains"
    version = APIVersion(1, 0)
    toolchains: List[Toolchain_1_0] = dataclasses.field(default_factory=list)


@dataclasses.dataclass(frozen=True)
class Compiler_1_1(Compiler_1_0):
    """
    ..versionadded:: 4.3.0
    """

    commandFragment: Optional[str] = None


@dataclasses.dataclass(frozen=True)
class Toolchain_1_1(Toolchain_1_0):
    """
    ..versionadded:: 4.3.0
    """

    compiler: Compiler_1_1


@dataclasses.dataclass(frozen=True)
class Toolchains_1_1(Toolchains_1_0):
    """
    ..versionadded:: 4.3.0
    """

    version = APIVersion(1, 1)
    toolchains: List[Toolchain_1_1] = dataclasses.field(default_factory=list)  # type: ignore[assignment]


Toolchains: TypeAlias = Union[Toolchains_1_0, Toolchains_1_1]
