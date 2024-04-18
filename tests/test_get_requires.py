from __future__ import annotations

import importlib.util
import shutil
import sys
import sysconfig
from pathlib import Path
from typing import Any

import pytest

from scikit_build_core.build import (
    get_requires_for_build_editable,
    get_requires_for_build_sdist,
    get_requires_for_build_wheel,
)
from scikit_build_core.builder.get_requires import GetRequires

ninja = [] if sysconfig.get_platform().startswith("win") else ["ninja>=1.5"]


def which_mock(name: str) -> str | None:
    if name in {"ninja", "ninja-build", "cmake3", "samu", "gmake", "make"}:
        return None
    if name == "cmake":
        return "cmake/path"
    return None


@pytest.fixture(autouse=True)
def protect_get_requires(fp, monkeypatch):
    """
    Protect get_requires from actually calling anything variable during tests.
    """
    # This needs to be passed due to packaging.tags 22 extra checks if macos 10.16 is reported
    fp.pass_command([sys.executable, fp.any()])
    monkeypatch.setattr(shutil, "which", which_mock)
    monkeypatch.delenv("CMAKE_GENERATOR", raising=False)

    orig_find_spec = importlib.util.find_spec

    def find_spec(name: str, package: str | None = None) -> Any:
        if name in {"cmake", "ninja"}:
            return None
        return orig_find_spec(name, package)

    monkeypatch.setattr(importlib.util, "find_spec", find_spec)


def test_get_requires_parts(fp):
    fp.register(
        [Path("cmake/path"), "-E", "capabilities"],
        stdout='{"version":{"string":"3.14.0"}}',
    )
    assert set(GetRequires().cmake()) == {"cmake>=3.15"}
    assert set(GetRequires().ninja()) == {*ninja}


def test_get_requires_parts_uneeded(fp):
    fp.register(
        [Path("cmake/path"), "-E", "capabilities"],
        stdout='{"version":{"string":"3.18.0"}}',
    )
    assert set(GetRequires().cmake()) == set()
    assert set(GetRequires().ninja()) == {*ninja}


def test_get_requires_parts_settings(fp):
    fp.register(
        [Path("cmake/path"), "-E", "capabilities"],
        stdout='{"version":{"string":"3.18.0"}}',
    )
    config = {"cmake.version": ">=3.20"}
    assert set(GetRequires.from_config_settings(config).cmake()) == {"cmake>=3.20"}
    assert set(GetRequires.from_config_settings(config).ninja()) == {*ninja}


def test_get_requires_parts_pyproject(fp, monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    tmp_path.joinpath("pyproject.toml").write_text(
        """
        [tool.scikit-build.cmake]
        version = ">=3.21"
        """
    )
    fp.register(
        [Path("cmake/path"), "-E", "capabilities"],
        stdout='{"version":{"string":"3.18.0"}}',
    )

    assert set(GetRequires().cmake()) == {"cmake>=3.21"}
    assert set(GetRequires().ninja()) == {*ninja}


def test_get_requires_parts_pyproject_old(fp, monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    tmp_path.joinpath("pyproject.toml").write_text(
        """
        
        [tool.scikit-build]
        minimum-version = "0.0"
        cmake.minimum-version = "3.21"
        """
    )
    fp.register(
        [Path("cmake/path"), "-E", "capabilities"],
        stdout='{"version":{"string":"3.18.0"}}',
    )

    assert set(GetRequires().cmake()) == {"cmake>=3.21"}
    assert set(GetRequires().ninja()) == {*ninja}


def test_get_requires_for_build_sdist(fp):
    fp.register(
        [Path("cmake/path"), "-E", "capabilities"],
        stdout='{"version":{"string":"3.14.0"}}',
    )
    assert set(get_requires_for_build_sdist({})) == set()


def test_get_requires_for_build_sdist_cmake(fp):
    expected = {"cmake>=3.15", *ninja}
    fp.register(
        [Path("cmake/path"), "-E", "capabilities"],
        stdout='{"version":{"string":"3.14.0"}}',
    )
    assert set(get_requires_for_build_sdist({"sdist.cmake": "True"})) == expected


def test_get_requires_for_build_wheel(fp):
    expected = {"cmake>=3.15", *ninja}
    fp.register(
        [Path("cmake/path"), "-E", "capabilities"],
        stdout='{"version":{"string":"3.14.0"}}',
    )
    assert set(get_requires_for_build_wheel({})) == expected


def test_get_requires_for_build_wheel_pure(fp):
    fp.register(
        [Path("cmake/path"), "-E", "capabilities"],
        stdout='{"version":{"string":"3.14.0"}}',
    )
    assert set(get_requires_for_build_wheel({"wheel.cmake": "False"})) == set()


def test_get_requires_for_build_editable(fp):
    expected = {"cmake>=3.15", *ninja}
    fp.register(
        [Path("cmake/path"), "-E", "capabilities"],
        stdout='{"version":{"string":"3.14.0"}}',
    )
    assert set(get_requires_for_build_editable({})) == expected


def test_get_requires_for_build_editable_pure(fp):
    fp.register(
        [Path("cmake/path"), "-E", "capabilities"],
        stdout='{"version":{"string":"3.14.0"}}',
    )
    assert set(get_requires_for_build_editable({"wheel.cmake": "False"})) == set()
