import dataclasses
from pathlib import Path
from typing import List

from .common import Paths


@dataclasses.dataclass
class Input:
    path: Path
    isGenerated: bool = False
    isExternal: bool = False
    isCMake: bool = False


@dataclasses.dataclass
class CMakeFiles:
    kind: str
    paths: Paths
    inputs: List[Input]
