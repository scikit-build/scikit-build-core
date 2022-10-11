from __future__ import annotations

import shutil
import sys
from pathlib import Path

from scikit_build_core.cmake import CMake
from scikit_build_core.errors import ScikitBuildError
from scikit_build_core.settings.cmake_settings import read_settings

__all__ = ["get_requires_for_build_wheel"]


def __dir__() -> list[str]:
    return __all__


def get_requires_for_build_wheel(
    # pylint: disable-next=unused-argument
    config_settings: dict[str, str | list[str]]
    | None = None
) -> list[str]:

    settings = read_settings(Path("pyproject.toml"), config_settings or {})

    packages = []
    try:
        CMake.default_search(minimum_version=settings.cmake.min_version, module=False)
    except ScikitBuildError:
        packages.append(f"cmake>={settings.cmake.min_version}")

    ninja_min = settings.ninja.min_version
    if not sys.platform.startswith("win"):
        ninja = shutil.which("ninja")
        if ninja is None:
            packages.append("ninja" if ninja_min == "0.0" else f"ninja>={ninja_min}")
        elif ninja_min != "0.0":
            raise NotImplementedError("Ninja limits not yet implemented")

    return packages
