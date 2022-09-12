from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from scikit_build_core.cmake import CMake, CMakeConfig
from scikit_build_core.file_api.converter import read_index
from scikit_build_core.file_api.query import stateless_query

DIR = Path(__file__).parent.absolute()


def test_simple_pure(tmp_path):
    build_dir = tmp_path / "build"
    install_dir = tmp_path / "install"

    cmake = CMake(minimum_version="3.15")
    config = CMakeConfig(
        cmake,
        source_dir=DIR / "simple_pure",
        build_dir=build_dir,
    )

    reply_dir = stateless_query(config.build_dir)

    config.configure()

    index = read_index(reply_dir)
    assert index is not None

    config.build()

    if not sys.platform.startswith("win32"):
        result = subprocess.run(
            [str(build_dir / "simple_pure")],
            capture_output=True,
            text=True,
            check=False,
        )
        assert result.returncode == 0
        assert result.stdout == "0 one 2 three \n"

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
