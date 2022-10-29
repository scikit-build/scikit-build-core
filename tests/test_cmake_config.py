from __future__ import annotations

import os
import shutil
import sys
from collections.abc import Generator
from pathlib import Path

import cmake
import pytest
from packaging.version import Version

from scikit_build_core.cmake import CMake, CMakeConfig
from scikit_build_core.errors import CMakeNotFoundError

DIR = Path(__file__).parent.resolve()


def configure_args(
    config: CMakeConfig, *, init: bool = False
) -> Generator[str, None, None]:
    cmake_path = Path(cmake.CMAKE_BIN_DIR) / "cmake"
    yield os.fspath(cmake_path)
    yield f"-S{config.source_dir}"
    yield f"-B{config.build_dir}"

    if init:
        cmake_init = config.build_dir / "CMakeInit.txt"
        yield f"-C{cmake_init}"

    if not sys.platform.startswith("win32"):
        yield "-GNinja"

    if config.prefix_dirs:
        yield "-DCMAKE_PREFIX_PATH={}".format(
            ";".join(str(p) for p in config.prefix_dirs)
        )


@pytest.mark.configure
def test_init_cache(fp, tmp_path):
    cmake_path = Path(cmake.CMAKE_BIN_DIR) / "cmake"
    fp.register([os.fspath(cmake_path), "--version"], stdout="3.14.0")

    config = CMakeConfig(
        CMake.default_search(),
        source_dir=DIR / "packages/simple_pure",
        build_dir=tmp_path / "build",
    )
    config.init_cache(
        {"SKBUILD": True, "SKBUILD_VERSION": "1.0.0", "SKBUILD_PATH": config.source_dir}
    )

    cmd = list(configure_args(config, init=True))
    if not sys.platform.startswith("win32"):
        cmd.append("-DCMAKE_BUILD_TYPE=Release")

    print("Registering:", *cmd)
    fp.register(cmd)
    config.configure()

    cmake_init = config.build_dir / "CMakeInit.txt"
    assert (
        cmake_init.read_text()
        == f"""\
set(SKBUILD ON CACHE BOOL "")
set(SKBUILD_VERSION [===[1.0.0]===] CACHE STRING "")
set(SKBUILD_PATH [===[{config.source_dir}]===] CACHE PATH "")
"""
    )


@pytest.mark.configure
def test_too_old(fp, monkeypatch):
    monkeypatch.setattr(shutil, "which", lambda x: None)
    cmake_path = Path(cmake.CMAKE_BIN_DIR) / "cmake"
    fp.register([os.fspath(cmake_path), "--version"], stdout="3.14.0")
    print(cmake_path)

    with pytest.raises(CMakeNotFoundError) as excinfo:
        CMake.default_search(minimum_version=Version("3.15"))
    assert "Could not find CMake with version >= 3.15" in excinfo.value.args[0]


@pytest.mark.configure
def test_cmake_args(tmp_path, fp):
    cmake_path = Path(cmake.CMAKE_BIN_DIR) / "cmake"
    fp.register([os.fspath(cmake_path), "--version"], stdout="3.15.0")

    config = CMakeConfig(
        CMake.default_search(),
        source_dir=DIR / "packages/simple_pure",
        build_dir=tmp_path / "build",
    )

    cmd = list(configure_args(config))
    if not sys.platform.startswith("win32"):
        cmd.append("-DCMAKE_BUILD_TYPE=Release")
    cmd.append("-DSOMETHING=one")
    print("Registering:", *cmd)
    fp.register(cmd)

    config.configure(cmake_args=["-DSOMETHING=one"])

    assert len(fp.calls) == 2
