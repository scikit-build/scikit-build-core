import dataclasses
from typing import List

__all__ = ["ScikitBuildSettings", "NinjaSettings", "CMakeSettings"]


def __dir__() -> List[str]:
    return __all__


@dataclasses.dataclass
class NinjaSettings:
    #: The minimum version of Ninja to use. If Ninja is older than this, it will
    #: be upgraded via PyPI if possible. An empty string will disable this check.
    minimum_version: str = "1.5"


@dataclasses.dataclass
class CMakeSettings:
    #: The minimum version of CMake to use. If CMake is older than this, it will
    #: be upgraded via PyPI if possible. An empty string will disable this check.
    minimum_version: str = "3.15"


@dataclasses.dataclass
class LogggingSettings:
    #: The logging level to display.
    level: str = "WARNING"


@dataclasses.dataclass
class ScikitBuildSettings:
    cmake: CMakeSettings
    ninja: NinjaSettings
    logging: LogggingSettings

    #: The ABI version to target. The default (empty string) will use the default
    #: ABI version for the Python version. You can also set this to "cp37" to
    #: enable the CPython 3.7+ Stable ABI / Limited API. Or you can set it to
    #: "py3" or "py2.py3" to ignore Python ABI compatibility. For the stable ABI,
    #: the CMake variable SKBUILD_SOABI will be set to abi3 on Unix-like systems
    #: (empty on Windows).
    abi_tag: str = ""
