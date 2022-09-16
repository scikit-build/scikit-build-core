import dataclasses
from pathlib import Path


@dataclasses.dataclass
class APIVersion:
    major: int
    minor: int


@dataclasses.dataclass
class Paths:
    source: Path
    build: Path
