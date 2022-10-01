import dataclasses
from pathlib import Path
from typing import List, Optional

from .common import APIVersion

__all__ = ["Implicit", "Compiler", "Toolchain", "Toolchains"]


def __dir__() -> List[str]:
    return __all__


@dataclasses.dataclass
class Implicit:
    includeDirectories: List[Path] = dataclasses.field(default_factory=list)
    linkDirectories: List[Path] = dataclasses.field(default_factory=list)
    linkFrameworkDirectories: List[Path] = dataclasses.field(default_factory=list)
    linkLibraries: List[Path] = dataclasses.field(default_factory=list)


@dataclasses.dataclass
class Compiler:
    implicit: Implicit
    path: Optional[Path] = None
    id: Optional[str] = None
    version: Optional[str] = None
    target: Optional[str] = None


@dataclasses.dataclass
class Toolchain:
    language: str  # Unique, since CMake supports one toolchain per language
    compiler: Compiler
    sourceFileExtensions: List[str] = dataclasses.field(default_factory=list)


@dataclasses.dataclass
class Toolchains:
    kind: str
    version: APIVersion
    toolchains: List[Toolchain] = dataclasses.field(default_factory=list)
