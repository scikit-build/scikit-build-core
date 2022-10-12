import dataclasses
from typing import List

__all__ = ["ScikitBuildSettings", "NinjaSettings", "CMakeSettings"]


def __dir__() -> List[str]:
    return __all__


@dataclasses.dataclass
class NinjaSettings:
    min_version: str = "0.0"


@dataclasses.dataclass
class CMakeSettings:
    min_version: str = "3.15"


@dataclasses.dataclass
class ScikitBuildSettings:
    cmake: CMakeSettings
    ninja: NinjaSettings
