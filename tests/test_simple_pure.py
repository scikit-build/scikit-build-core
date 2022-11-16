from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest
from packaging.version import Version

from scikit_build_core.cmake import CMake, CMaker

DIR = Path(__file__).parent.absolute()


@pytest.fixture(scope="session")
def config(tmp_path_factory):
    tmp_path = tmp_path_factory.mktemp("build")

    build_dir = tmp_path / "build"

    cmake = CMake.default_search(minimum_version=Version("3.15"))
    config = CMaker(
        cmake,
        source_dir=DIR / "packages/simple_pure",
        build_dir=build_dir,
        build_type="Release",
    )

    config.configure()

    config.build()

    return config


@pytest.mark.compile
@pytest.mark.configure
@pytest.mark.skipif(
    sys.platform.startswith("win32") or sys.platform.startswith("cygwin"),
    reason="Paths different in build dir on Windows",
)
def test_bin_in_config(config):
    result = subprocess.run(
        [str(config.build_dir / "simple_pure")],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0
    assert result.stdout == "0 one 2 three \n"


# TODO: figure out why gmake is reporting no rule to make simple_pure.cpp
@pytest.mark.compile
@pytest.mark.configure
@pytest.mark.xfail(
    sys.platform.startswith("cygwin"), strict=False, reason="No idea why this fails"
)
def test_install(config):
    install_dir = config.build_dir.parent / "install"
    config.install(install_dir)

    result = subprocess.run(
        [str(install_dir / "bin/simple_pure")],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0
    assert result.stdout == "0 one 2 three \n"


@pytest.mark.configure
def test_variable_defined(tmp_path, capfd):
    build_dir = tmp_path / "build"

    cmake = CMake.default_search(minimum_version=Version("3.15"))
    config = CMaker(
        cmake,
        source_dir=DIR / "packages/simple_pure",
        build_dir=build_dir,
        build_type="Release",
    )
    config.init_cache({"SKBUILD": True})
    config.configure(defines={"SKBUILD2": True})

    out = capfd.readouterr().out
    assert "SKBUILD is defined to ON" in out
    assert "SKBUILD2 is defined to ON" in out
