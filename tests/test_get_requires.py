from __future__ import annotations

import sysconfig
from pathlib import Path
from typing import TYPE_CHECKING

import pytest

from scikit_build_core.build import (
    get_requires_for_build_editable,
    get_requires_for_build_sdist,
    get_requires_for_build_wheel,
)
from scikit_build_core.builder.get_requires import GetRequires

if TYPE_CHECKING:
    from pytest_subprocess import FakeProcess

ninja = [] if sysconfig.get_platform().startswith("win") else ["ninja>=1.5"]


@pytest.fixture(autouse=True)
def protect_get_requires_autouse(protect_get_requires: None):
    """
    Autouse this fixture in this test.
    """


def test_get_requires_parts(fp: FakeProcess):
    fp.register(
        [Path("cmake/path"), "-E", "capabilities"],
        stdout='{"version":{"string":"3.14.0"}}',
    )
    assert set(GetRequires().cmake()) == {"cmake>=3.15"}
    assert set(GetRequires().ninja()) == {*ninja}


def test_get_requires_parts_uneeded(fp: FakeProcess):
    fp.register(
        [Path("cmake/path"), "-E", "capabilities"],
        stdout='{"version":{"string":"3.18.0"}}',
    )
    assert set(GetRequires().cmake()) == set()
    assert set(GetRequires().ninja()) == {*ninja}


def test_get_requires_parts_settings(fp: FakeProcess):
    fp.register(
        [Path("cmake/path"), "-E", "capabilities"],
        stdout='{"version":{"string":"3.18.0"}}',
    )
    config = {"cmake.version": ">=3.20"}
    assert set(GetRequires.from_config_settings(config).cmake()) == {"cmake>=3.20"}
    assert set(GetRequires.from_config_settings(config).ninja()) == {*ninja}


def test_get_requires_parts_pyproject(
    fp: FakeProcess, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
):
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


def test_get_requires_parts_pyproject_old(
    fp: FakeProcess, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
):
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


def test_get_requires_for_build_sdist(fp: FakeProcess):
    fp.register(
        [Path("cmake/path"), "-E", "capabilities"],
        stdout='{"version":{"string":"3.14.0"}}',
    )
    assert set(get_requires_for_build_sdist({})) == set()


def test_get_requires_for_build_sdist_cmake(fp: FakeProcess):
    expected = {"cmake>=3.15", *ninja}
    fp.register(
        [Path("cmake/path"), "-E", "capabilities"],
        stdout='{"version":{"string":"3.14.0"}}',
    )
    assert set(get_requires_for_build_sdist({"sdist.cmake": "True"})) == expected


def test_get_requires_for_build_wheel(fp: FakeProcess):
    expected = {"cmake>=3.15", *ninja}
    fp.register(
        [Path("cmake/path"), "-E", "capabilities"],
        stdout='{"version":{"string":"3.14.0"}}',
    )
    assert set(get_requires_for_build_wheel({})) == expected


def test_get_requires_for_build_wheel_pure(fp: FakeProcess):
    fp.register(
        [Path("cmake/path"), "-E", "capabilities"],
        stdout='{"version":{"string":"3.14.0"}}',
    )
    assert set(get_requires_for_build_wheel({"wheel.cmake": "False"})) == set()


def test_get_requires_for_build_editable(fp: FakeProcess):
    expected = {"cmake>=3.15", *ninja}
    fp.register(
        [Path("cmake/path"), "-E", "capabilities"],
        stdout='{"version":{"string":"3.14.0"}}',
    )
    assert set(get_requires_for_build_editable({})) == expected


def test_get_requires_for_build_editable_pure(fp: FakeProcess):
    fp.register(
        [Path("cmake/path"), "-E", "capabilities"],
        stdout='{"version":{"string":"3.14.0"}}',
    )
    assert set(get_requires_for_build_editable({"wheel.cmake": "False"})) == set()
