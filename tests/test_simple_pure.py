from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

from scikit_build_core.cmake import CMake, CMakeConfig
from scikit_build_core.file_api.loadfile import load_file

DIR = Path(__file__).parent.absolute()


@pytest.fixture(scope="session")
def config(tmp_path_factory):
    tmp_path = tmp_path_factory.mktemp("build")

    build_dir = tmp_path / "build"

    cmake = CMake(minimum_version="3.15")
    config = CMakeConfig(
        cmake,
        source_dir=DIR / "simple_pure",
        build_dir=build_dir,
    )

    config.query()
    config.configure()

    config.build()

    return config


@pytest.mark.skipif(
    sys.implementation.name == "pypy", reason="cattrs does not support pypy for 22.1"
)
def test_cattrs_comparison(config):
    from scikit_build_core.file_api._cattrs_converter import read_index

    reply_dir = config.query()

    cattrs_index = read_index(reply_dir)
    index = load_file(reply_dir)
    assert index == cattrs_index


@pytest.mark.skipif(
    sys.platform.startswith("win32"),
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


def test_variable_defined(tmp_path, capfd):
    build_dir = tmp_path / "build"

    cmake = CMake(minimum_version="3.15")
    config = CMakeConfig(
        cmake,
        source_dir=DIR / "simple_pure",
        build_dir=build_dir,
    )
    config.init_cache({"SKBUILD": True})
    config.configure({"SKBUILD2": True})

    out = capfd.readouterr().out
    assert "SKBUILD is defined to ON" in out
    assert "SKBUILD2 is defined to ON" in out
