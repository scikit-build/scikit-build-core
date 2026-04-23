import dataclasses
from pathlib import Path
from typing import List, Optional

from .._common import ObjectKindSubType, Paths

__all__ = ["Target"]


def __dir__() -> List[str]:
    return __all__


@dataclasses.dataclass(frozen=True)
class Artifact:
    path: Path


@dataclasses.dataclass(frozen=True)
class Prefix:
    path: Path


@dataclasses.dataclass(frozen=True)
class Destination:
    path: Path
    backtrace: Optional[int] = None


@dataclasses.dataclass(frozen=True)
class Install:
    prefix: Prefix
    destinations: List[Destination]


@dataclasses.dataclass(frozen=True)
class CommandFragment:
    fragment: str
    role: str


@dataclasses.dataclass(frozen=True)
class Sysroot:
    path: Path


@dataclasses.dataclass(frozen=True)
class Link:
    language: str
    commandFragments: Optional[List[CommandFragment]]
    lto: Optional[bool] = None
    sysroot: Optional[Sysroot] = None


@dataclasses.dataclass(frozen=True)
class Archive:
    commandFragments: Optional[List[CommandFragment]] = dataclasses.field(
        default_factory=list
    )
    lto: Optional[bool] = None


@dataclasses.dataclass(frozen=True)
class Dependency:
    id: str
    backtrace: Optional[int] = None


@dataclasses.dataclass(frozen=True)
class Source:
    path: Path
    compileGroupIndex: Optional[int] = None
    sourceGroupIndex: Optional[int] = None
    isGenerated: Optional[bool] = None
    backtrace: Optional[int] = None


@dataclasses.dataclass(frozen=True)
class Target(ObjectKindSubType):
    name: str
    id: str
    type: str
    paths: Paths
    sources = List[Source]
    nameOnDisk: Optional[Path] = None
    artifacts: List[Artifact] = dataclasses.field(default_factory=list)
    isGeneratorProvided: Optional[bool] = None
    install: Optional[Install] = None
    link: Optional[Link] = None
    archive: Optional[Archive] = None
    dependencies: List[Dependency] = dataclasses.field(default_factory=list)
