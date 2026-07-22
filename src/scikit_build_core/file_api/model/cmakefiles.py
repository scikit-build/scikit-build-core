__lazy_modules__ = {f"{__spec__.parent}.common", "pathlib", "typing"}

import dataclasses
from pathlib import Path
from typing import List, Optional

from .common import APIVersion, Paths

__all__ = ["CMakeFiles", "GlobDependent", "Input"]


def __dir__() -> List[str]:
    return __all__


@dataclasses.dataclass(frozen=True)
class Input:
    path: Path
    isGenerated: bool = False
    isExternal: bool = False
    isCMake: bool = False


@dataclasses.dataclass(frozen=True)
class GlobDependent:
    expression: str
    recurse: bool = False
    listDirectories: bool = False
    followSymlinks: bool = False
    relative: Optional[str] = None
    paths: List[Path] = dataclasses.field(default_factory=list)


@dataclasses.dataclass(frozen=True)
class CMakeFiles:
    kind: str
    version: APIVersion
    paths: Paths
    inputs: List[Input]
    globsDependent: List[GlobDependent] = dataclasses.field(default_factory=list)
