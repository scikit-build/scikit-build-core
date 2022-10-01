import dataclasses
from typing import List

__all__ = ["CMakeSettings"]


def __dir__() -> List[str]:
    return __all__


@dataclasses.dataclass
class CMakeSettings:
    min_version: str = "3.15"
