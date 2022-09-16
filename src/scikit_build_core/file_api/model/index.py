import dataclasses
from pathlib import Path
from typing import List, Optional

from .cache import Cache
from .cmakefiles import CMakeFiles
from .codemodel import CodeModel
from .common import APIVersion
from .toolchains import Toolchains


@dataclasses.dataclass
class CMakeVersion:
    major: int
    minor: int
    patch: int
    suffix: str
    string: str
    isDirty: bool


@dataclasses.dataclass
class CMakePaths:
    cmake: Path
    ctest: Path
    cpack: Path
    root: Path


@dataclasses.dataclass
class Generator:
    multiConfig: bool
    name: str
    platform: Optional[str] = None


@dataclasses.dataclass
class CMake:
    version: CMakeVersion
    paths: CMakePaths
    generator: Generator


@dataclasses.dataclass
class Reply:
    codemodel_v2: Optional[CodeModel]
    cache_v2: Optional[Cache]
    cmakefiles_v1: Optional[CMakeFiles]
    toolchains_v1: Optional[Toolchains]


@dataclasses.dataclass
class Object:
    kind: str
    version: APIVersion
    jsonFile: Path


@dataclasses.dataclass
class Index:
    cmake: CMake
    objects: List[Object]
    reply: Reply
