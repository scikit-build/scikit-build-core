__lazy_modules__ = {f"{__spec__.parent}.common", "pathlib", "typing"}

import dataclasses
from pathlib import Path
from typing import Optional, Union

from .common import APIVersion, Paths

__all__ = [
    "BacktraceGraph",
    "Directory",
    "InstallPath",
    "InstallRule",
    "Node",
    "Target",
]


def __dir__() -> list[str]:
    return __all__


@dataclasses.dataclass(frozen=True)
class Target:
    id: str
    index: int


@dataclasses.dataclass(frozen=True)
class InstallPath:
    from_: Path
    to: Path


@dataclasses.dataclass(frozen=True)
class InstallRule:
    component: str
    type: str
    destination: Optional[Path] = None
    paths: list[Union[Path, InstallPath]] = dataclasses.field(default_factory=list)
    isExcludeFromAll: bool = False
    isForAllComponents: bool = False
    isOptional: bool = False
    targetId: Optional[str] = None
    targetIndex: Optional[int] = None
    targetIsImportLibrary: bool = False
    targetInstallNamelink: Optional[str] = None
    exportName: Optional[str] = None
    exportTargets: list[Target] = dataclasses.field(default_factory=list)
    runtimeDependencySetName: Optional[str] = None
    runtimeDependencySetType: Optional[str] = None
    fileSetName: Optional[str] = None
    fileSetType: Optional[str] = None
    fileSetDirectories: list[Path] = dataclasses.field(default_factory=list)
    fileSetTarget: Optional[Target] = None
    cxxModuleBmiTarget: Optional[Target] = None
    scriptFile: Optional[Path] = None
    backtrace: Optional[int] = None


@dataclasses.dataclass(frozen=True)
class Node:
    file: int
    line: Optional[int] = None
    command: Optional[int] = None
    parent: Optional[int] = None


@dataclasses.dataclass(frozen=True)
class BacktraceGraph:
    nodes: list[Node]
    commands: list[str]
    files: list[Path]


@dataclasses.dataclass(frozen=True)
class Directory:
    paths: Paths
    installers: list[InstallRule]
    backtraceGraph: BacktraceGraph
    codemodelVersion: Optional[APIVersion] = None
