from __future__ import annotations

import dataclasses
import os
import subprocess
import sys
from pathlib import Path

if sys.version_info < (3, 8):
    import importlib_metadata as metadata
else:
    from importlib import metadata

import distlib.wheel
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


@dataclasses.dataclass
class VirtualEnvWrap:
    base: Path

    def run(self, expression: str, *, capture: bool = True) -> str:
        assert capture, "Always capture for now"
        env = os.environ.copy()
        env["PATH"] = f"{self.base / 'bin'}{os.pathsep}{env['PATH']}"
        env["VIRTUAL_ENV"] = str(self.base)
        return subprocess.run(
            expression,
            check=True,
            capture_output=capture,
            text=True,
            shell=True,
            env=env,
        ).stdout.strip()


@pytest.fixture
def virtualenv(tmp_path: Path) -> VirtualEnvWrap:
    path = tmp_path / "venv"
    from virtualenv import cli_run

    cli_run([str(path)])

    return VirtualEnvWrap(path)


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


def pytest_report_header() -> str:
    interesting_packages = {
        "packaging",
        "pyproject_metadata",
        "distlib",
        "pathspec",
        "rich",
        "build",
        "pip",
        "setuptools",
        "wheel",
        "pybind11",
    }
    valid = []
    for package in interesting_packages:
        try:
            version = metadata.version(package)  # type: ignore[no-untyped-call]
        except ModuleNotFoundError:
            continue
        valid.append(f"{package}=={version}")
    reqs = " ".join(sorted(valid))
    pkg_line = f"installed packages of interest: {reqs}"

    wheel = distlib.wheel.Wheel()
    wheel.abi = [distlib.wheel.ABI]
    wheel.pyver = [distlib.wheel.IMPVER]
    wheel.arch = [distlib.wheel.ARCH]
    wheel_line = f"default wheelname: {wheel.filename}"

    return "\n".join([pkg_line, wheel_line])
