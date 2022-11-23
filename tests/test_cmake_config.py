from __future__ import annotations

import functools
import os
import shutil
from collections.abc import Generator
from pathlib import Path

import pytest
from packaging.version import Version

from scikit_build_core.cmake import CMake, CMaker
from scikit_build_core.errors import CMakeNotFoundError

DIR = Path(__file__).parent.resolve()


@functools.lru_cache(1)
def cmake_path() -> str:
    try:
        import cmake
    except ModuleNotFoundError:
        cmake_str = shutil.which("cmake")
        print(cmake_str)
        if cmake_str is None:
            pytest.skip("cmake must be installed for this test")
        return os.fspath(Path(cmake_str).resolve())

    return os.fspath(Path(cmake.CMAKE_BIN_DIR) / "cmake")


def configure_args(config: CMaker, *, init: bool = False) -> Generator[str, None, None]:

    yield cmake_path()
    yield f"-S{config.source_dir}"
    yield f"-B{config.build_dir}"

    if init:
        cmake_init = config.build_dir / "CMakeInit.txt"
        yield f"-C{cmake_init}"

    if config.single_config:
        yield f"-DCMAKE_BUILD_TYPE={config.build_type}"

    if config.module_dirs:
        yield "-DCMAKE_MODULE_PATH:PATH={}".format(
            ";".join(str(p).replace("\\", "/") for p in config.module_dirs)
        )

    if config.prefix_dirs:
        yield "-DCMAKE_PREFIX_PATH:PATH={}".format(
            ";".join(str(p).replace("\\", "/") for p in config.prefix_dirs)
        )


@pytest.mark.configure
def test_init_cache(fp, tmp_path):
    fp.register([cmake_path(), "--version"], stdout="3.14.0")

    config = CMaker(
        CMake.default_search(),
        source_dir=DIR / "packages/simple_pure",
        build_dir=tmp_path / "build",
        build_type="Release",
    )
    config.init_cache(
        {"SKBUILD": True, "SKBUILD_VERSION": "1.0.0", "SKBUILD_PATH": config.source_dir}
    )

    cmd = list(configure_args(config, init=True))
    print("Registering:", *cmd)
    fp.register(cmd)
    config.configure()

    cmake_init = config.build_dir / "CMakeInit.txt"
    source_dir_str = str(config.source_dir).replace("\\", "/")
    assert (
        cmake_init.read_text()
        == f"""\
set(SKBUILD ON CACHE BOOL "")
set(SKBUILD_VERSION [===[1.0.0]===] CACHE STRING "")
set(SKBUILD_PATH [===[{source_dir_str}]===] CACHE PATH "")
"""
    )


@pytest.mark.configure
def test_too_old(fp, monkeypatch):
    monkeypatch.setattr(shutil, "which", lambda x: None)
    fp.register([cmake_path(), "--version"], stdout="3.14.0")
    print(cmake_path)

    with pytest.raises(CMakeNotFoundError) as excinfo:
        CMake.default_search(minimum_version=Version("3.15"))
    assert "Could not find CMake with version >= 3.15" in excinfo.value.args[0]


@pytest.mark.configure
def test_cmake_args(tmp_path, fp):
    fp.register([cmake_path(), "--version"], stdout="3.15.0")

    config = CMaker(
        CMake.default_search(),
        source_dir=DIR / "packages/simple_pure",
        build_dir=tmp_path / "build",
        build_type="Release",
    )

    cmd = list(configure_args(config))
    cmd.append("-DSOMETHING=one")
    print("Registering:", *cmd)
    fp.register(cmd)

    config.configure(cmake_args=["-DSOMETHING=one"])

    assert len(fp.calls) == 2


@pytest.mark.configure
def test_cmake_paths(tmp_path, fp):
    fp.register([cmake_path(), "--version"], stdout="3.15.0")

    config = CMaker(
        CMake.default_search(),
        source_dir=DIR / "packages/simple_pure",
        build_dir=tmp_path / "build",
        build_type="Release",
        prefix_dirs=[tmp_path / "prefix"],
        module_dirs=[tmp_path / "module"],
    )

    cmd = list(configure_args(config))
    print("Registering:", *cmd)
    fp.register(cmd)

    config.configure()

    assert len(fp.calls) == 2
