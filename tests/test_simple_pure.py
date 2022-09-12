from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from scikit_build_core.cmake import CMake, CMakeConfig
from scikit_build_core.file_api.loadfile import load_file
from scikit_build_core.file_api.model._cattrs_converter import read_index

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

    reply_dir = config.query()
    config.configure()

    cattrs_index = read_index(reply_dir)
    index = load_file(reply_dir)
    assert index == cattrs_index

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
