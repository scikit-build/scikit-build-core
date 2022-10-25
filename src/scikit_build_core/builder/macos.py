from __future__ import annotations

import os
import platform

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
    plat_target = normalize_macos_version(platform.mac_ver()[0])
    if target is None:
        return plat_target

    env_target = ".".join(target.split(".")[:2]) if "." in target else f"{target}.0"
    try:
        norm_env_target = normalize_macos_version(env_target)
    except ValueError:
        return plat_target

    return norm_env_target if norm_env_target > plat_target else plat_target


def get_macosx_deployment_target() -> str:
    """
    Get the MACOSX_DEPLOYMENT_TARGET environment variable or use the version
    Python was built with. Suggestion: do not touch MACOSX_DEPLOYMENT_TARGET
    if it's set.
    """
    return ".".join(str(d) for d in get_macosx_deployment_target_tuple())
