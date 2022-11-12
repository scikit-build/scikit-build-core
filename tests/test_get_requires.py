from __future__ import annotations

import os
import shutil
import sys
from pathlib import Path

from scikit_build_core.builder.get_requires import cmake_ninja_for_build_wheel

ninja = [] if sys.platform.startswith("win") else ["ninja>=1.5"]


def which_mock(name: str) -> str | None:
    if name in ("ninja", "ninja-build", "cmake3", "samu", "gmake", "make"):
        return None
    if name == "cmake":
        return "cmake/path"
    return None


def test_get_requires_for_build_wheel(fp, monkeypatch):
    cmake = Path("cmake/path").resolve()
    monkeypatch.setattr(shutil, "which", which_mock)
    fp.register([os.fspath(cmake), "--version"], stdout="3.14.0")
    assert cmake_ninja_for_build_wheel() == ["cmake>=3.15", *ninja]


def test_get_requires_for_build_wheel_uneeded(fp, monkeypatch):
    cmake = Path("cmake/path").resolve()
    monkeypatch.setattr(shutil, "which", which_mock)
    fp.register([os.fspath(cmake), "--version"], stdout="3.18.0")
    assert cmake_ninja_for_build_wheel() == [*ninja]


def test_get_requires_for_build_wheel_settings(fp, monkeypatch):
    cmake = Path("cmake/path").resolve()
    monkeypatch.setattr(shutil, "which", which_mock)
    fp.register([os.fspath(cmake), "--version"], stdout="3.18.0")
    config = {"cmake.minimum-version": "3.20"}
    assert cmake_ninja_for_build_wheel(config) == [
        "cmake>=3.20",
        *ninja,
    ]


def test_get_requires_for_build_wheel_pyproject(fp, monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    tmp_path.joinpath("pyproject.toml").write_text(
        """
        [tool.scikit-build.cmake]
        minimum-version = "3.21"
        """
    )
    cmake = Path("cmake/path").resolve()
    monkeypatch.setattr(shutil, "which", which_mock)
    fp.register([os.fspath(cmake), "--version"], stdout="3.18.0")
    assert cmake_ninja_for_build_wheel() == ["cmake>=3.21", *ninja]
