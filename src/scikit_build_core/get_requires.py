from __future__ import annotations

import shutil
from pathlib import Path

from scikit_build_core.cmake import CMake
from scikit_build_core.errors import ScikitBuildError
from scikit_build_core.settings.convert import read_cmake_settings


def get_requires_for_build_wheel(
    # pylint: disable-next=unused-argument
    config_settings: dict[str, str | list[str]]
    | None = None
) -> list[str]:

    cmake_settings = read_cmake_settings(Path("pyproject.toml"), config_settings or {})

    packages = []
    try:
        CMake(minimum_version=cmake_settings.min_version, module=False)
    except ScikitBuildError:
        packages.append(f"cmake>={cmake_settings.min_version}")

    ninja = shutil.which("ninja")
    if ninja is None:
        packages.append("ninja")

    return packages
