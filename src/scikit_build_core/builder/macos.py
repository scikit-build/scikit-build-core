from __future__ import annotations

import os
import platform

__all__ = ["get_macosx_deployment_target"]


def __dir__() -> list[str]:
    return __all__


def normalize_macos_version(version: str) -> str:
    """
    Set minor version to 0 if major is 11+.
    """
    major, minor = version.split(".")[0:2]
    minor = "0" if int(major) >= 11 else minor
    return f"{major}.{minor}"


def get_macosx_deployment_target() -> str:
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
        float(env_target)
    except ValueError:
        return plat_target

    norm_env_target = normalize_macos_version(env_target)
    return (
        norm_env_target if float(norm_env_target) > float(plat_target) else plat_target
    )
