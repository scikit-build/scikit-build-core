from __future__ import annotations

import os
import platform
from typing import NamedTuple

from .._logging import logger

__all__ = ["MacOSVer", "get_macosx_deployment_target", "normalize_macos_version"]


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


def get_macosx_deployment_target(*, arm: bool) -> MacOSVer:
    """
    Get the MACOSX_DEPLOYMENT_TARGET environment variable. If not set, use the
    current macOS version. If arm=True, then this will always return at least (11, 0).
    Versions after 11 will be normalized to 0 for minor version.
    """
    target = os.environ.get("MACOSX_DEPLOYMENT_TARGET", None)
    plat_ver_str, _, _ = platform.mac_ver()
    plat_target = normalize_macos_version(plat_ver_str, arm=arm)
    if target is None:
        logger.debug("MACOSX_DEPLOYMENT_TARGET not set, using {}", plat_target)
        return plat_target

    env_target = ".".join(target.split(".")[:2]) if "." in target else f"{target}.0"
    try:
        norm_env_target = normalize_macos_version(env_target, arm=arm)
    except ValueError:
        msg = "MACOSX_DEPLOYMENT_TARGET not readable ({}), using {} instead"
        logger.warning(msg, env_target, plat_target)
        return plat_target

    logger.debug("MACOSX_DEPLOYMENT_TARGET is set to {}", env_target)
    return norm_env_target
