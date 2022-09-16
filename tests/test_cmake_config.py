from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

from scikit_build_core.cmake import CMake, CMakeConfig, get_cmake_path
from scikit_build_core.errors import CMakeConfigError

DIR = Path(__file__).parent.absolute()

# Due to https://github.com/scikit-build/cmake-python-distributions/pull/279
# this is outside of the functions for now.
cmake_path = get_cmake_path()


def configure_args(config, *, init=False):
    yield os.fspath(cmake_path)
    yield f"-S{config.source_dir}"
    yield f"-B{config.build_dir}"

    if init:
        cmake_init = config.build_dir / "CMakeInit.txt"
        yield f"-C{cmake_init}"

    if not sys.platform.startswith("win32"):
        yield "-GNinja"


@pytest.mark.configure
def test_init_cache(fp, tmp_path):
    fp.register([os.fspath(cmake_path), "--version"], stdout="3.14.0")

    config = CMakeConfig(
        CMake(), source_dir=DIR / "simple_pure", build_dir=tmp_path / "build"
    )
    config.init_cache(
        {"SKBUILD": True, "SKBUILD_VERSION": "1.0.0", "SKBUILD_PATH": config.source_dir}
    )

    cmd = list(configure_args(config, init=True))

    print("Registering:", *cmd)
    fp.register(cmd)
    config.configure()

    cmake_init = config.build_dir / "CMakeInit.txt"
    assert (
        cmake_init.read_text()
        == f"""\
set(SKBUILD "ON" CACHE BOOL "")
set(SKBUILD_VERSION "1.0.0" CACHE STRING "")
set(SKBUILD_PATH "{config.source_dir}" CACHE PATH "")
"""
    )


@pytest.mark.configure
def test_too_old(fp):
    fp.register([os.fspath(cmake_path), "--version"], stdout="3.14.0")

    with pytest.raises(CMakeConfigError) as excinfo:
        CMake(minimum_version="3.15")
    assert (
        "CMake version 3.14.0 is less than minimum version 3.15"
        in excinfo.value.args[0]
    )


@pytest.mark.configure
def test_cmake_args(tmp_path, fp):
    fp.register([os.fspath(cmake_path), "--version"], stdout="3.15.0")

    config = CMakeConfig(
        CMake(), source_dir=DIR / "simple_pure", build_dir=tmp_path / "build"
    )

    cmd = list(configure_args(config))
    cmd.append("-DCMAKE_BUILD_TYPE=Debug")
    print("Registering:", *cmd)
    fp.register(cmd)

    config.configure(cmake_args=["-DCMAKE_BUILD_TYPE=Debug"])

    assert len(fp.calls) == 2
