from __future__ import annotations

__lazy_modules__ = {
    f"{(__spec__.parent or '').rsplit('.', 1)[0]}._logging",
    "platform",
    "re",
}

import os
import platform
import re
from typing import NamedTuple

from .._logging import logger

TYPE_CHECKING = False
if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence

__all__ = [
    "MacOSVer",
    "get_cmake_osx_deployment_target",
    "get_macosx_deployment_target",
    "normalize_macos_version",
]


class MacOSVer(NamedTuple):
    major: int
    minor: int

    def __str__(self) -> str:
        return f"{self.major}.{self.minor}"


def __dir__() -> list[str]:
    return __all__


def normalize_macos_version(version: str, *, arm: bool) -> MacOSVer:
    """
    Set minor version to 0 if major is 11+.
    """
    if "." not in version:
        version = f"{version}.0"
    major, minor = (int(d) for d in version.split(".")[:2])
    major = max(major, 11) if arm else major
    minor = 0 if major >= 11 else minor
    return MacOSVer(major, minor)


def get_cmake_osx_deployment_target(
    cmake_defines: Mapping[str, str] | None = None,
    cmake_args: Sequence[str] = (),
) -> str | None:
    """
    Find an explicit ``CMAKE_OSX_DEPLOYMENT_TARGET`` known before the build
    directory exists: a ``cmake.define`` entry or a ``-DCMAKE_OSX_DEPLOYMENT_TARGET=``
    in ``cmake.args``. The args value wins over the define, mirroring CMake's own
    command-line-over-cache precedence. Settings in ``CMakeLists.txt`` or a
    toolchain file cannot be seen here and are not honored.
    """
    target: str | None = None
    if cmake_defines is not None:
        target = cmake_defines.get("CMAKE_OSX_DEPLOYMENT_TARGET", None)
    for arg in cmake_args:
        match = re.fullmatch(r"-D\s*CMAKE_OSX_DEPLOYMENT_TARGET(?::[^=]*)?=(.*)", arg)
        if match:
            target = match.group(1)
    return target


def get_macosx_deployment_target(
    *,
    arm: bool,
    cmake_defines: Mapping[str, str] | None = None,
    cmake_args: Sequence[str] = (),
) -> MacOSVer:
    """
    Get the deployment target used for the wheel platform tag. An explicit
    ``CMAKE_OSX_DEPLOYMENT_TARGET`` from ``cmake.define`` or ``cmake.args`` wins;
    otherwise the ``MACOSX_DEPLOYMENT_TARGET`` environment variable is used (this
    is the fallback default CMake itself applies). If neither is set, the current
    macOS version is used. If arm=True, then this will always return at least
    (11, 0). Versions after 11 will be normalized to 0 for minor version.
    """
    plat_ver_str, _, _ = platform.mac_ver()
    plat_target = normalize_macos_version(plat_ver_str, arm=arm)

    cmake_target = get_cmake_osx_deployment_target(cmake_defines, cmake_args)
    if cmake_target is not None:
        try:
            norm_cmake_target = normalize_macos_version(cmake_target, arm=arm)
        except ValueError:
            msg = "CMAKE_OSX_DEPLOYMENT_TARGET not readable ({}), trying MACOSX_DEPLOYMENT_TARGET / current version instead"
            logger.warning(msg, cmake_target)
        else:
            logger.debug("CMAKE_OSX_DEPLOYMENT_TARGET is set to {}", cmake_target)
            return norm_cmake_target

    target = os.environ.get("MACOSX_DEPLOYMENT_TARGET", None)
    if target is None:
        logger.debug("MACOSX_DEPLOYMENT_TARGET not set, using {}", plat_target)
        return plat_target

    try:
        norm_env_target = normalize_macos_version(target, arm=arm)
    except ValueError:
        msg = "MACOSX_DEPLOYMENT_TARGET not readable ({}), using {} instead"
        logger.warning(msg, target, plat_target)
        return plat_target

    logger.debug("MACOSX_DEPLOYMENT_TARGET is set to {}", target)
    return norm_env_target
