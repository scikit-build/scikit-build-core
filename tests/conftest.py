from __future__ import annotations

import importlib.util
import subprocess
import sys
from pathlib import Path

import pytest

DIR = Path(__file__).parent.resolve()
BASE = DIR.parent


@pytest.fixture(scope="session")
def pep518_wheelhouse(tmppath_factory: pytest.TempPathFactory) -> str:
    wheelhouse = tmppath_factory.mktemp("wheelhouse")

    subprocess.run(
        [
            sys.executable,
            "-m",
            "pip",
            "wheel",
            "--wheel-dir",
            str(wheelhouse),
            f"{BASE}[pyproject]",
        ],
        check=True,
    )

    subprocess.run(
        [
            sys.executable,
            "-m",
            "pip",
            "download",
            "-q",
            "-d",
            str(wheelhouse),
            "build",
            "cmake",
            "ninja",
            "numpy",
            "pybind11",
            "rich",
            "setuptools",
            "wheel",
        ],
        check=True,
    )
    return str(wheelhouse)


@pytest.fixture
def isolated(pep518_wheelhouse: str, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PIP_FIND_LINKS", pep518_wheelhouse)
    monkeypatch.setenv("PIP_NO_INDEX", "true")


has_pyvenv = importlib.util.find_spec("pytest_virtualenv") is not None

if not has_pyvenv:

    @pytest.fixture
    def virtualenv() -> None:
        pytest.skip("pytest-virtualenv not available")


def pytest_collection_modifyitems(items: list[pytest.Item]) -> None:
    for item in items:
        # Ensure all tests using virtualenv are marked as such
        if "virtualenv" in getattr(item, "fixturenames", ()):
            item.add_marker(pytest.mark.virtualenv)

        # Ensure all tests with a pep518 name are marked as isolated
        if "pep518" in item.nodeid and item.get_closest_marker("isolated") is None:
            raise AssertionError("PEP 518 tests must be isolated")

        # Marking with an isolated marker turns on the isolated fixture
        if item.get_closest_marker("isolated") is not None:
            item.add_marker(pytest.mark.usefixtures("isolated"))
