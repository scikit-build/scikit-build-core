import subprocess
import sys
from pathlib import Path

import pytest

DIR = Path(__file__).parent.resolve()
BASE = DIR.parent


@pytest.fixture(scope="session")
def pep518_wheelhouse(tmpdir_factory):
    wheelhouse = tmpdir_factory.mktemp("wheelhouse")
    dist = tmpdir_factory.mktemp("dist")
    subprocess.run(
        [sys.executable, "-m", "build", "--wheel", "--outdir", str(dist)],
        cwd=str(BASE),
        check=True,
    )
    (wheel_path,) = dist.visit("*.whl")
    subprocess.run(
        [
            sys.executable,
            "-m",
            "pip",
            "download",
            "-q",
            "-d",
            str(wheelhouse),
            str(wheel_path),
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
            "setuptools",
            "wheel",
            "ninja",
            "pybind11",
            "cmake",
            "numpy",
            "exceptiongroup",
            "packaging",
            "tomli",
            "typing-extensions",
        ],
        check=True,
    )
    return str(wheelhouse)


@pytest.fixture
def pep518(pep518_wheelhouse, monkeypatch):
    monkeypatch.setenv("PIP_FIND_LINKS", pep518_wheelhouse)
    monkeypatch.setenv("PIP_NO_INDEX", "true")
    return pep518_wheelhouse
