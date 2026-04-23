import dataclasses
from pathlib import Path
from typing import List, Optional

__all__ = ["BacktraceGraph"]


def __dir__() -> List[str]:
    return __all__


@dataclasses.dataclass(frozen=True)
class Node:
    file: int
    line: Optional[int] = None
    command: Optional[int] = None
    parent: Optional[int] = None


# This one is not a json-backed file, it is just shared
# between directory and target
@dataclasses.dataclass(frozen=True)
class BacktraceGraph:
    nodes: List[Node]
    commands: List[str]
    files: List[Path]
