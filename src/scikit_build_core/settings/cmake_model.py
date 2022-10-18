import dataclasses
from typing import List

__all__ = ["ScikitBuildSettings", "NinjaSettings", "CMakeSettings"]


def __dir__() -> List[str]:
    return __all__


@dataclasses.dataclass
class NinjaSettings:
    minimum_version: str = "1.5"


@dataclasses.dataclass
class CMakeSettings:
    minimum_version: str = "3.15"


@dataclasses.dataclass
class ScikitBuildSettings:
    cmake: CMakeSettings
    ninja: NinjaSettings
