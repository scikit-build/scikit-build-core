from __future__ import annotations

import shutil
import sys
from pathlib import Path

from scikit_build_core.cmake import CMake
from scikit_build_core.errors import ScikitBuildError
from scikit_build_core.settings.cmake_settings import read_cmake_settings

__all__ = ["get_requires_for_build_wheel"]


def __dir__() -> list[str]:
    return __all__


def get_requires_for_build_wheel(
    # pylint: disable-next=unused-argument
    config_settings: dict[str, str | list[str]]
    | None = None
) -> list[str]:

    cmake_settings = read_cmake_settings(Path("pyproject.toml"), config_settings or {})

    packages = []
    try:
        CMake.default_search(minimum_version=cmake_settings.min_version, module=False)
    except ScikitBuildError:
        packages.append(f"cmake>={cmake_settings.min_version}")

    if not sys.platform.startswith("win"):
        ninja = shutil.which("ninja")
        if ninja is None:
            packages.append("ninja")

    return packages
