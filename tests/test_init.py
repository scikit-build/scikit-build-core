from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from scikit_build_core.__main__ import main
from scikit_build_core._compat import tomllib
from scikit_build_core.init.__main__ import BACKENDS

if TYPE_CHECKING:
    from pathlib import Path

# Source filename written into the package for each backend.
SOURCES = {
    "c": "_core.c",
    "abi3": "_core.c",
    "pybind11": "_core.cpp",
    "nanobind": "_core.cpp",
    "cython": "_core.pyx",
    "swig": "_core.c",
    "fortran": "_core.f",
}

EXTRA_REQUIRES = {
    "c": [],
    "abi3": [],
    "pybind11": ["pybind11"],
    "nanobind": ["nanobind"],
    "cython": ["cython", "cython-cmake"],
    "swig": ["swig"],
    "fortran": ["numpy", "f2py-cmake"],
}


@pytest.mark.parametrize("backend", BACKENDS)
def test_init_generates_files(backend: str, tmp_path: Path) -> None:
    project = tmp_path / "proj"
    main(["init", str(project), "--backend", backend, "--name", "my-pkg"])

    pkg = project / "src" / "my_pkg"
    assert (project / "CMakeLists.txt").is_file()
    assert (
        pkg / "__init__.py"
    ).read_text() == 'from ._core import square\n\n__all__ = ["square"]\n'
    assert (pkg / SOURCES[backend]).is_file()
    if backend == "swig":
        assert (pkg / "_core.i").is_file()

    data = tomllib.loads((project / "pyproject.toml").read_text())
    assert data["project"]["name"] == "my-pkg"
    assert data["build-system"]["requires"] == [
        "scikit-build-core",
        *EXTRA_REQUIRES[backend],
    ]

    cmake = (project / "CMakeLists.txt").read_text()
    assert "_core" in cmake
    assert "${SKBUILD_PROJECT_NAME}" in cmake


def test_init_default_name_from_directory(tmp_path: Path) -> None:
    project = tmp_path / "Spam.Eggs"
    main(["init", str(project), "--backend", "c"])

    data = tomllib.loads((project / "pyproject.toml").read_text())
    assert data["project"]["name"] == "spam-eggs"
    assert (project / "src" / "spam_eggs" / "_core.c").is_file()


def test_init_refuses_nonempty_directory(tmp_path: Path) -> None:
    (tmp_path / "existing.txt").write_text("hi")
    with pytest.raises(SystemExit):
        main(["init", str(tmp_path), "--backend", "c"])
    assert not (tmp_path / "pyproject.toml").exists()


def test_init_force_into_nonempty_directory(tmp_path: Path) -> None:
    (tmp_path / "existing.txt").write_text("hi")
    main(["init", str(tmp_path), "--backend", "c", "--name", "my-pkg", "--force"])
    assert (tmp_path / "pyproject.toml").is_file()
    assert (tmp_path / "existing.txt").is_file()


def test_init_non_interactive_requires_backend(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr("sys.stdin.isatty", lambda: False)
    with pytest.raises(SystemExit):
        main(["init", str(tmp_path)])
    assert not (tmp_path / "pyproject.toml").exists()


def test_init_interactive_selection(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr("sys.stdin.isatty", lambda: True)
    # First an invalid entry, then "3" which is the "c" backend.
    answers = iter(["bogus", "3"])
    monkeypatch.setattr("builtins.input", lambda _prompt: next(answers))

    project = tmp_path / "proj"
    main(["init", str(project), "--name", "my-pkg"])
    assert BACKENDS[2] == "c"
    assert (project / "src" / "my_pkg" / "_core.c").is_file()
