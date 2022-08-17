from __future__ import annotations

import subprocess
from pathlib import Path

from scikit_build_core.cmake import CMake, CMakeConfig

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
    config.configure()
    config.build()

    result = subprocess.run(
        [build_dir / "simple_pure"], capture_output=True, text=True, check=True
    )
    assert result.stdout == "0 one 2 three \n"

    config.install(install_dir)

    result = subprocess.run(
        [install_dir / "bin/simple_pure"], capture_output=True, text=True, check=True
    )
    assert result.stdout == "0 one 2 three \n"
