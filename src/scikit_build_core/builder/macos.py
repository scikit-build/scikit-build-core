from __future__ import annotations

import os
import sysconfig

from .._logging import logger

__all__ = ["get_macosx_deployment_target", "get_macosx_deployment_target_tuple"]


def __dir__() -> list[str]:
    return __all__


def normalize_macos_version(version: str) -> tuple[int, int]:
    """
    Set minor version to 0 if major is 11+.
    """
    if "." not in version:
        version = f"{version}.0"
    major, minor = (int(d) for d in version.split(".")[:2])
    minor = 0 if major >= 11 else minor
    return major, minor


def get_macosx_deployment_target_tuple() -> tuple[int, int]:
    """
    Get the MACOSX_DEPLOYMENT_TARGET environment variable or use the version
    Python was built with. Suggestion: do not touch MACOSX_DEPLOYMENT_TARGET
    if it's set.
    """
    target = os.environ.get("MACOSX_DEPLOYMENT_TARGET", None)
    plat_ver_str = sysconfig.get_platform().rsplit("-", 1)[0].split("-", 1)[1]
    plat_target = normalize_macos_version(plat_ver_str)
    if target is None:
        logger.debug("MACOSX_DEPLOYMENT_TARGET not set, using {}", plat_target)
        return plat_target

    env_target = ".".join(target.split(".")[:2]) if "." in target else f"{target}.0"
    try:
        norm_env_target = normalize_macos_version(env_target)
    except ValueError:
        msg = "MACOSX_DEPLOYMENT_TARGET not readable ({}), using {} instead"
        logger.warning(msg, env_target, plat_target)
        return plat_target

    if norm_env_target < plat_target:
        msg = "MACOSX_DEPLOYMENT_TARGET ({}) is less than that which Python was compiled with, {}, using that instead"
        logger.warning(msg, env_target, plat_target)
        return plat_target

    logger.debug("MACOSX_DEPLOYMENT_TARGET is set to {}", env_target)
    return norm_env_target


def get_macosx_deployment_target() -> str:
    """
    Get the MACOSX_DEPLOYMENT_TARGET environment variable or use the version
    Python was built with. Suggestion: do not touch MACOSX_DEPLOYMENT_TARGET
    if it's set.
    """
    return ".".join(str(d) for d in get_macosx_deployment_target_tuple())
