import dataclasses
from pathlib import Path
from typing import List, Optional

from .cache import Cache
from .cmakefiles import CMakeFiles
from .codemodel import CodeModel
from .common import APIVersion
from .toolchains import Toolchains

__all__ = [
    "CMake",
    "CMakePaths",
    "CMakeVersion",
    "Generator",
    "Index",
    "Object",
    "Reply",
]


def __dir__() -> List[str]:
    return __all__


@dataclasses.dataclass(frozen=True)
class CMakeVersion:
    major: int
    minor: int
    patch: int
    suffix: str
    string: str
    isDirty: bool


@dataclasses.dataclass(frozen=True)
class CMakePaths:
    cmake: Path
    ctest: Path
    cpack: Path
    root: Path


@dataclasses.dataclass(frozen=True)
class Generator:
    name: str
    multiConfig: Optional[bool] = None
    platform: Optional[str] = None


@dataclasses.dataclass(frozen=True)
class CMake:
    version: CMakeVersion
    paths: CMakePaths
    generator: Generator


@dataclasses.dataclass(frozen=True)
class Reply:
    codemodel_v2: Optional[CodeModel]
    cache_v2: Optional[Cache]
    cmakefiles_v1: Optional[CMakeFiles]
    toolchains_v1: Optional[Toolchains]


@dataclasses.dataclass(frozen=True)
class Object:
    kind: str
    version: APIVersion
    jsonFile: Path


@dataclasses.dataclass(frozen=True)
class Index:
    cmake: CMake
    objects: List[Object]
    reply: Reply
