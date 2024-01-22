import dataclasses
from pathlib import Path
from typing import List, Optional

from .common import APIVersion

__all__ = ["Compiler", "Implicit", "Toolchain", "Toolchains"]


def __dir__() -> List[str]:
    return __all__


@dataclasses.dataclass(frozen=True)
class Implicit:
    includeDirectories: List[Path] = dataclasses.field(default_factory=list)
    linkDirectories: List[Path] = dataclasses.field(default_factory=list)
    linkFrameworkDirectories: List[Path] = dataclasses.field(default_factory=list)
    linkLibraries: List[Path] = dataclasses.field(default_factory=list)


@dataclasses.dataclass(frozen=True)
class Compiler:
    implicit: Implicit
    path: Optional[Path] = None
    id: Optional[str] = None
    version: Optional[str] = None
    target: Optional[str] = None


@dataclasses.dataclass(frozen=True)
class Toolchain:
    language: str  # Unique, since CMake supports one toolchain per language
    compiler: Compiler
    sourceFileExtensions: List[str] = dataclasses.field(default_factory=list)


@dataclasses.dataclass(frozen=True)
class Toolchains:
    kind: str = "toolchains"
    version: APIVersion = APIVersion(1, 0)
    toolchains: List[Toolchain] = dataclasses.field(default_factory=list)
