from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest

from scikit_build_core._shutil import Run
from scikit_build_core.cmake import CMake, CMakeConfig
from scikit_build_core.errors import CMakeConfigError

DIR = Path(__file__).parent.absolute()


def test_init_cache(monkeypatch, tmp_path):
    def fake_run(self, args, kwargs, capture):
        return SimpleNamespace(stdout="3.15.0")

    monkeypatch.setattr(Run, "_run", fake_run)
    config = CMakeConfig(
        CMake(), source_dir=DIR / "simple_pure", build_dir=tmp_path / "build"
    )
    config.init_cache(
        {"SKBUILD": True, "SKBUILD_VERSION": "1.0.0", "SKBUILD_PATH": config.source_dir}
    )
    config.configure()

    assert (
        config.build_dir.joinpath("CMakeInit.txt").read_text()
        == f"""\
set(SKBUILD "ON" CACHE BOOL "")
set(SKBUILD_VERSION "1.0.0" CACHE STRING "")
set(SKBUILD_PATH "{config.source_dir}" CACHE PATH "")
"""
    )


def test_too_old(monkeypatch):
    def fake_run(self, args, kwargs, capture):
        return SimpleNamespace(stdout="3.14.0")

    monkeypatch.setattr(Run, "_run", fake_run)

    with pytest.raises(CMakeConfigError) as excinfo:
        CMake(minimum_version="3.15")
    assert (
        "CMake version 3.14.0 is less than minimum version 3.15"
        in excinfo.value.args[0]
    )
