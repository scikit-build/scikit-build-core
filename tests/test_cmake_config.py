from __future__ import annotations

from pathlib import Path

import pytest

from scikit_build_core.cmake import CMake, CMakeConfig, get_cmake_path
from scikit_build_core.errors import CMakeConfigError

DIR = Path(__file__).parent.absolute()


def test_init_cache(fp, tmp_path):
    cmake_path = get_cmake_path()
    fp.register([str(cmake_path), "--version"], stdout="3.14.0")

    config = CMakeConfig(
        CMake(), source_dir=DIR / "simple_pure", build_dir=tmp_path / "build"
    )
    config.init_cache(
        {"SKBUILD": True, "SKBUILD_VERSION": "1.0.0", "SKBUILD_PATH": config.source_dir}
    )

    cmake_init = config.build_dir / "CMakeInit.txt"
    fp.register(
        [
            f"{cmake_path}",
            f"-S{config.source_dir}",
            f"-B{config.build_dir}",
            f"-C{cmake_init}",
            "-GNinja",
        ]
    )
    config.configure()

    assert (
        cmake_init.read_text()
        == f"""\
set(SKBUILD "ON" CACHE BOOL "")
set(SKBUILD_VERSION "1.0.0" CACHE STRING "")
set(SKBUILD_PATH "{config.source_dir}" CACHE PATH "")
"""
    )


def test_too_old(fp):
    cmake_path = get_cmake_path()
    fp.register([str(cmake_path), "--version"], stdout="3.14.0")

    with pytest.raises(CMakeConfigError) as excinfo:
        CMake(minimum_version="3.15")
    assert (
        "CMake version 3.14.0 is less than minimum version 3.15"
        in excinfo.value.args[0]
    )


def test_cmake_args(tmp_path, fp):
    cmake_path = get_cmake_path()
    fp.register([str(cmake_path), "--version"], stdout="3.15.0")

    config = CMakeConfig(
        CMake(), source_dir=DIR / "simple_pure", build_dir=tmp_path / "build"
    )

    fp.register(
        [
            f"{cmake_path}",
            f"-S{config.source_dir}",
            f"-B{config.build_dir}",
            "-GNinja",
            "-DCMAKE_BUILD_TYPE=Debug",
        ]
    )
    config.configure(cmake_args=["-DCMAKE_BUILD_TYPE=Debug"])

    assert len(fp.calls) == 2
