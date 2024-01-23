import dataclasses
from pathlib import Path
from typing import List

from .common import Paths

__all__ = ["CMakeFiles", "Input"]


def __dir__() -> List[str]:
    return __all__


@dataclasses.dataclass(frozen=True)
class Input:
    path: Path
    isGenerated: bool = False
    isExternal: bool = False
    isCMake: bool = False


@dataclasses.dataclass(frozen=True)
class CMakeFiles:
    kind: str
    paths: Paths
    inputs: List[Input]
