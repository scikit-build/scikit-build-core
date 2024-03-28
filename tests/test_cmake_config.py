from __future__ import annotations

import os
import shutil
from pathlib import Path
from typing import TYPE_CHECKING

import pytest
from packaging.specifiers import SpecifierSet
from packaging.version import Version

from scikit_build_core.cmake import CMake, CMaker
from scikit_build_core.errors import CMakeNotFoundError

if TYPE_CHECKING:
    from collections.abc import Generator

DIR = Path(__file__).parent.resolve()


def configure_args(config: CMaker, *, init: bool = False) -> Generator[str, None, None]:
    yield f"-S{config.source_dir}"
    yield f"-B{config.build_dir}"

    if config.single_config:
        yield f"-DCMAKE_BUILD_TYPE:STRING={config.build_type}"

    if init:
        cmake_init = config.build_dir / "CMakeInit.txt"
        yield f"-C{cmake_init}"


@pytest.mark.configure()
def test_init_cache(fp, tmp_path):
    fp.register(
        [fp.program("cmake"), "-E", "capabilities"],
        stdout='{"version":{"string":"3.14.0"}}',
    )
    fp.register(
        [fp.program("cmake3"), "-E", "capabilities"],
        stdout='{"version":{"string":"3.14.0"}}',
    )

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
    print("Registering: cmake", *cmd)
    fp.register([fp.program("cmake"), *cmd])
    fp.register([fp.program("cmake3"), *cmd])
    config.configure()

    cmake_init = config.build_dir / "CMakeInit.txt"
    source_dir_str = str(config.source_dir).replace("\\", "/")
    assert (
        cmake_init.read_text()
        == f"""\
set(SKBUILD ON CACHE BOOL "" FORCE)
set(SKBUILD_VERSION [===[1.0.0]===] CACHE STRING "" FORCE)
set(SKBUILD_PATH [===[{source_dir_str}]===] CACHE PATH "" FORCE)
"""
    )


@pytest.mark.configure()
def test_too_old(fp, monkeypatch):
    monkeypatch.setattr(shutil, "which", lambda _: None)
    fp.register(
        [fp.program("cmake"), "-E", "capabilities"],
        stdout='{"version":{"string":"3.14.0"}}',
    )
    fp.register(
        [fp.program("cmake3"), "-E", "capabilities"],
        stdout='{"version":{"string":"3.14.0"}}',
    )

    with pytest.raises(CMakeNotFoundError) as excinfo:
        CMake.default_search(version=SpecifierSet(">=3.15"))
    assert "Could not find CMake with version >=3.15" in excinfo.value.args[0]


@pytest.mark.configure()
def test_cmake_args(tmp_path, fp):
    fp.register(
        [fp.program("cmake"), "-E", "capabilities"],
        stdout='{"version":{"string":"3.15.0"}}',
    )
    fp.register(
        [fp.program("cmake3"), "-E", "capabilities"],
        stdout='{"version":{"string":"3.15.0"}}',
    )

    config = CMaker(
        CMake.default_search(),
        source_dir=DIR / "packages/simple_pure",
        build_dir=tmp_path / "build",
        build_type="Release",
    )

    cmd = list(configure_args(config))
    cmd.append("-DSOMETHING=one")
    print("Registering: cmake", *cmd)
    fp.register([fp.program("cmake"), *cmd])
    fp.register([fp.program("cmake3"), *cmd])

    config.configure(cmake_args=["-DSOMETHING=one"])

    assert len(fp.calls) == 2


@pytest.mark.configure()
def test_cmake_paths(tmp_path, fp):
    fp.register(
        [fp.program("cmake"), "-E", "capabilities"],
        stdout='{"version":{"string":"3.15.0"}}',
    )
    fp.register(
        [fp.program("cmake3"), "-E", "capabilities"],
        stdout='{"version":{"string":"3.15.0"}}',
    )

    config = CMaker(
        CMake.default_search(),
        source_dir=DIR / "packages/simple_pure",
        build_dir=tmp_path / "build",
        build_type="Release",
        prefix_dirs=[tmp_path / "prefix"],
        module_dirs=[tmp_path / "module"],
    )

    cmd = list(configure_args(config))
    print("Registering: cmake", *cmd)
    fp.register([fp.program("cmake"), *cmd])
    fp.register([fp.program("cmake3"), *cmd])

    config.configure()

    assert len(fp.calls) == 2


def test_get_cmake_via_envvar(monkeypatch: pytest.MonkeyPatch, fp):
    monkeypatch.setattr("shutil.which", lambda x: x)
    cmake_path = Path("some-prog")
    fp.register(
        [cmake_path, "-E", "capabilities"], stdout='{"version":{"string":"3.20.0"}}'
    )
    monkeypatch.setenv("CMAKE_EXECUTABLE", str(cmake_path))
    result = CMake.default_search(env=os.environ)
    assert result.cmake_path == cmake_path
    assert result.version == Version("3.20.0")
