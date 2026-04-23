import dataclasses
from pathlib import Path
from typing import List, Optional

from ._common import APIVersion, Paths
from .target import Target

__all__ = [
    "CodeModel",
    "Configuration",
    "Directory",
    "Project",
    "StringCMakeVersion",
]


def __dir__() -> List[str]:
    return __all__


@dataclasses.dataclass(frozen=True)
class StringCMakeVersion:
    string: str


@dataclasses.dataclass(frozen=True)
class Directory:
    source: Path
    build: Path
    projectIndex: int
    jsonFile: Optional[Path] = None
    parentIndex: Optional[int] = None
    childIndexes: List[int] = dataclasses.field(default_factory=list)
    targetIndexes: List[int] = dataclasses.field(default_factory=list)
    minimumCMakeVersion: Optional[StringCMakeVersion] = None
    hasInstallRule: bool = False


# Directory is currently not resolved automatically.


@dataclasses.dataclass(frozen=True)
class Project:
    name: str
    directoryIndexes: List[int]
    parentIndex: Optional[int] = None
    childIndexes: List[int] = dataclasses.field(default_factory=list)
    targetIndexes: List[int] = dataclasses.field(default_factory=list)


@dataclasses.dataclass(frozen=True)
class Configuration:
    name: str
    projects: List[Project]
    targets: List[Target]
    directories: List[Directory]


@dataclasses.dataclass(frozen=True)
class CodeModel:
    kind: str
    version: APIVersion
    paths: Paths
    configurations: List[Configuration]
