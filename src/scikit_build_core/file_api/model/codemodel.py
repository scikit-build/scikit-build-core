__lazy_modules__ = {
    f"{__spec__.parent}.common",
    f"{__spec__.parent}.directory",
    "pathlib",
    "typing",
}

import dataclasses
from pathlib import Path
from typing import List, Optional

from .common import APIVersion, Paths
from .directory import BacktraceGraph, InstallRule

__all__ = [
    "Archive",
    "Artifact",
    "CodeModel",
    "CommandFragment",
    "CompileCommandFragment",
    "CompileDependency",
    "CompileGroup",
    "Configuration",
    "Debugger",
    "Define",
    "Dependency",
    "Destination",
    "Directory",
    "FileSet",
    "Folder",
    "FromDependency",
    "Include",
    "Install",
    "LanguageStandard",
    "Launcher",
    "Link",
    "LinkLibrary",
    "PrecompileHeader",
    "Prefix",
    "Project",
    "Source",
    "SourceGroup",
    "StringCMakeVersion",
    "Sysroot",
    "Target",
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
    abstractTargetIndexes: List[int] = dataclasses.field(default_factory=list)
    minimumCMakeVersion: Optional[StringCMakeVersion] = None
    hasInstallRule: bool = False
    # From the "directory" object loaded via jsonFile:
    installers: List[InstallRule] = dataclasses.field(default_factory=list)
    backtraceGraph: Optional[BacktraceGraph] = None
    codemodelVersion: Optional[APIVersion] = None


@dataclasses.dataclass(frozen=True)
class Project:
    name: str
    directoryIndexes: List[int]
    parentIndex: Optional[int] = None
    childIndexes: List[int] = dataclasses.field(default_factory=list)
    targetIndexes: List[int] = dataclasses.field(default_factory=list)
    abstractTargetIndexes: List[int] = dataclasses.field(default_factory=list)


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
    commandFragments: Optional[List[CommandFragment]] = dataclasses.field(
        default_factory=list
    )
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
class FromDependency:
    id: str


@dataclasses.dataclass(frozen=True)
class LinkLibrary:
    # Exactly one of id or fragment is present
    id: Optional[str] = None
    fragment: Optional[str] = None
    backtrace: Optional[int] = None
    fromDependency: Optional[FromDependency] = None


@dataclasses.dataclass(frozen=True)
class CompileDependency:
    id: str
    backtrace: Optional[int] = None
    fromDependency: Optional[FromDependency] = None


@dataclasses.dataclass(frozen=True)
class Folder:
    name: str


@dataclasses.dataclass(frozen=True)
class Launcher:
    command: Path
    type: str
    arguments: List[str] = dataclasses.field(default_factory=list)


@dataclasses.dataclass(frozen=True)
class Debugger:
    workingDirectory: Optional[Path] = None


@dataclasses.dataclass(frozen=True)
class FileSet:
    name: str
    type: str
    visibility: str
    baseDirectories: List[Path] = dataclasses.field(default_factory=list)


@dataclasses.dataclass(frozen=True)
class SourceGroup:
    name: str
    sourceIndexes: List[int] = dataclasses.field(default_factory=list)
    interfaceSourceIndexes: List[int] = dataclasses.field(default_factory=list)


@dataclasses.dataclass(frozen=True)
class LanguageStandard:
    standard: str
    backtraces: List[int] = dataclasses.field(default_factory=list)


@dataclasses.dataclass(frozen=True)
class CompileCommandFragment:
    fragment: str
    backtrace: Optional[int] = None


@dataclasses.dataclass(frozen=True)
class Include:
    path: Path
    isSystem: Optional[bool] = None
    backtrace: Optional[int] = None


@dataclasses.dataclass(frozen=True)
class PrecompileHeader:
    header: Path
    backtrace: Optional[int] = None


@dataclasses.dataclass(frozen=True)
class Define:
    define: str
    backtrace: Optional[int] = None


@dataclasses.dataclass(frozen=True)
class CompileGroup:
    sourceIndexes: List[int]
    language: str
    languageStandard: Optional[LanguageStandard] = None
    compileCommandFragments: List[CompileCommandFragment] = dataclasses.field(
        default_factory=list
    )
    includes: List[Include] = dataclasses.field(default_factory=list)
    frameworks: List[Include] = dataclasses.field(default_factory=list)
    precompileHeaders: List[PrecompileHeader] = dataclasses.field(default_factory=list)
    defines: List[Define] = dataclasses.field(default_factory=list)
    sysroot: Optional[Sysroot] = None


@dataclasses.dataclass(frozen=True)
class Source:
    path: Path
    compileGroupIndex: Optional[int] = None
    sourceGroupIndex: Optional[int] = None
    isGenerated: Optional[bool] = None
    fileSetIndex: Optional[int] = None
    fileSetIndexes: List[int] = dataclasses.field(default_factory=list)
    backtrace: Optional[int] = None
    backtraces: List[int] = dataclasses.field(default_factory=list)


@dataclasses.dataclass(frozen=True)
class Target:
    name: str
    id: str
    type: str
    paths: Paths
    sources: List[Source] = dataclasses.field(default_factory=list)
    nameOnDisk: Optional[Path] = None
    artifacts: List[Artifact] = dataclasses.field(default_factory=list)
    isGeneratorProvided: Optional[bool] = None
    install: Optional[Install] = None
    link: Optional[Link] = None
    archive: Optional[Archive] = None
    dependencies: List[Dependency] = dataclasses.field(default_factory=list)
    backtrace: Optional[int] = None
    folder: Optional[Folder] = None
    launchers: List[Launcher] = dataclasses.field(default_factory=list)
    debugger: Optional[Debugger] = None
    imported: Optional[bool] = None
    local: Optional[bool] = None
    abstract: Optional[bool] = None
    symbolic: Optional[bool] = None
    linkLibraries: List[LinkLibrary] = dataclasses.field(default_factory=list)
    interfaceLinkLibraries: List[LinkLibrary] = dataclasses.field(default_factory=list)
    compileDependencies: List[CompileDependency] = dataclasses.field(
        default_factory=list
    )
    interfaceCompileDependencies: List[CompileDependency] = dataclasses.field(
        default_factory=list
    )
    objectDependencies: List[Dependency] = dataclasses.field(default_factory=list)
    orderDependencies: List[Dependency] = dataclasses.field(default_factory=list)
    fileSets: List[FileSet] = dataclasses.field(default_factory=list)
    interfaceSources: List[Source] = dataclasses.field(default_factory=list)
    sourceGroups: List[SourceGroup] = dataclasses.field(default_factory=list)
    compileGroups: List[CompileGroup] = dataclasses.field(default_factory=list)
    backtraceGraph: Optional[BacktraceGraph] = None
    codemodelVersion: Optional[APIVersion] = None
    # From the codemodel reference to this target:
    directoryIndex: Optional[int] = None
    projectIndex: Optional[int] = None


@dataclasses.dataclass(frozen=True)
class Configuration:
    name: str
    projects: List[Project]
    targets: List[Target]
    directories: List[Directory]
    abstractTargets: List[Target] = dataclasses.field(default_factory=list)


@dataclasses.dataclass(frozen=True)
class CodeModel:
    kind: str
    version: APIVersion
    paths: Paths
    configurations: List[Configuration]
