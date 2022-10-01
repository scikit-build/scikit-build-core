import dataclasses
from pathlib import Path
from typing import List, Optional

from .common import APIVersion, Paths

__all__ = [
    "Archive",
    "Artifact",
    "CodeModel",
    "CommandFragment",
    "Configuration",
    "Dependency",
    "Destination",
    "Directory",
    "Install",
    "Link",
    "Prefix",
    "Project",
    "Source",
    "StringCMakeVersion",
    "Sysroot",
    "Target",
]


def __dir__() -> List[str]:
    return __all__


@dataclasses.dataclass
class StringCMakeVersion:
    string: str


@dataclasses.dataclass
class Directory:
    source: Path
    build: Path
    jsonFile: Path
    projectIndex: int
    parentIndex: Optional[int] = None
    childIndexes: List[int] = dataclasses.field(default_factory=list)
    targetIndexes: List[int] = dataclasses.field(default_factory=list)
    minimumCMakeVersion: Optional[StringCMakeVersion] = None
    hasInstallRule: bool = False


# Directory is currently not resolved automatically.


@dataclasses.dataclass
class Project:
    name: str
    directoryIndexes: List[int]
    parentIndex: Optional[int] = None
    childIndexes: List[int] = dataclasses.field(default_factory=list)
    targetIndexes: List[int] = dataclasses.field(default_factory=list)


@dataclasses.dataclass
class Artifact:
    path: Path


@dataclasses.dataclass
class Prefix:
    path: Path


@dataclasses.dataclass
class Destination:
    path: Path
    backtrace: Optional[int] = None


@dataclasses.dataclass
class Install:
    prefix: Prefix
    destinations: List[Destination]


@dataclasses.dataclass
class CommandFragment:
    fragment: str
    role: str


@dataclasses.dataclass
class Sysroot:
    path: Path


@dataclasses.dataclass
class Link:
    language: str
    commandFragments: List[CommandFragment]
    lto: Optional[bool] = None
    sysroot: Optional[Sysroot] = None


@dataclasses.dataclass
class Archive:
    commandFragments: List[CommandFragment] = dataclasses.field(default_factory=list)
    lto: Optional[bool] = None


@dataclasses.dataclass
class Dependency:
    id: str
    backtrace: Optional[int] = None


@dataclasses.dataclass
class Source:
    path: Path
    compileGroupIndex: Optional[int] = None
    sourceGroupIndex: Optional[int] = None
    isGenerated: Optional[bool] = None
    backtrace: Optional[int] = None


@dataclasses.dataclass
class Target:
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


@dataclasses.dataclass
class Configuration:
    name: str
    directories: List[Directory]
    projects: List[Project]
    targets: List[Target]


@dataclasses.dataclass
class CodeModel:
    kind: str
    version: APIVersion
    paths: Paths
    configurations: List[Configuration]
