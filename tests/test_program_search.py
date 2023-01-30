from __future__ import annotations

import logging
from pathlib import Path

import pytest
from packaging.version import Version

from scikit_build_core.program_search import (
    best_program,
    get_cmake_programs,
    get_ninja_programs,
)


def test_get_cmake_programs_cmake_module(monkeypatch):
    cmake = pytest.importorskip("cmake")
    monkeypatch.setattr("shutil.which", lambda _: None)
    programs = list(get_cmake_programs())
    assert len(programs) == 1
    assert programs[0].path.name == "cmake"
    assert programs[0].version == Version(".".join(cmake.__version__.split(".")[:3]))


def test_get_ninja_programs_cmake_module(monkeypatch):
    ninja = pytest.importorskip("ninja")
    monkeypatch.setattr("shutil.which", lambda _: None)
    programs = list(get_ninja_programs())
    assert len(programs) == 1
    assert programs[0].path.name == "ninja"
    assert programs[0].version == Version(".".join(ninja.__version__.split(".")[:3]))


# There's a bug in Path.resolve() on Windows for Python <3.10 that causes it to
# return an relative path when the path is non-existent. But we don't care about
# that case, so we'll just do the same thing as the search does.


def test_get_cmake_programs_all(monkeypatch, fp):
    monkeypatch.setattr("shutil.which", lambda x: x)
    cmake_path = Path("cmake")
    cmake3_path = Path("cmake3")
    fp.register(
        [cmake_path, "--version"],
        stdout="cmake version 3.20.0\n\nCMake suite maintained and supported by Kitware (kitware.com/cmake).",
    )
    fp.register(
        [cmake3_path, "--version"],
        stdout="cmake version 3.19.0\n\nCMake suite maintained and supported by Kitware (kitware.com/cmake).",
    )
    programs = list(get_cmake_programs(module=False))
    assert len(programs) == 2
    assert programs[0].path.name == "cmake3"
    assert programs[0].version == Version("3.19.0")
    assert programs[1].path.name == "cmake"
    assert programs[1].version == Version("3.20.0")

    best1 = best_program(programs, minimum_version=None)
    assert best1
    assert best1.path.name == "cmake3"

    best2 = best_program(programs, minimum_version=Version("3.20.0"))
    assert best2
    assert best2.path.name == "cmake"


def test_get_ninja_programs_all(monkeypatch, fp):
    monkeypatch.setattr("shutil.which", lambda x: x if "ninja" in x else None)
    ninja_path = Path("ninja")
    ninja_build_path = Path("ninja-build")
    fp.register([ninja_path, "--version"], stdout="1.10.1.git.kitware.jobserver-1")
    fp.register([ninja_build_path, "--version"], stdout="1.8.2")
    programs = list(get_ninja_programs(module=False))
    assert len(programs) == 2
    assert programs[0].path.name == "ninja-build"
    assert programs[0].version == Version("1.8.2")
    assert programs[1].path.name == "ninja"
    assert programs[1].version == Version("1.10.1")

    best1 = best_program(programs, minimum_version=None)
    assert best1
    assert best1.path.name == "ninja-build"

    best2 = best_program(programs, minimum_version=Version("1.9"))
    assert best2
    assert best2.path.name == "ninja"


def test_get_cmake_programs_malformed(monkeypatch, fp, caplog):
    caplog.set_level(logging.WARNING)
    monkeypatch.setattr("shutil.which", lambda x: x)
    cmake_path = Path("cmake")
    cmake3_path = Path("cmake3")
    fp.register([cmake_path, "--version"], stdout="scrambled output\n")
    fp.register([cmake3_path, "--version"], stdout="cmake version 3.17.3\n")
    programs = list(get_cmake_programs(module=False))
    assert caplog.records
    assert "Could not determine CMake version" in str(caplog.records[0].msg)
    assert len(programs) == 2

    best_none = best_program(programs, minimum_version=None)
    assert best_none
    assert best_none.path.name == "cmake3"

    best_3_15 = best_program(programs, minimum_version=Version("3.15"))
    assert best_3_15
    assert best_3_15.path.name == "cmake3"

    best_3_20 = best_program(programs, minimum_version=Version("3.20"))
    assert best_3_20 is None
