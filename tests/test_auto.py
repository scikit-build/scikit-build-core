import pytest
from packaging.specifiers import SpecifierSet
from packaging.version import Version

from scikit_build_core.settings.auto_cmake_version import find_min_cmake_version
from scikit_build_core.settings.auto_requires import get_min_requires


def test_auto_requires_pkg_no_spec():
    reqlist = ["scikit-build-core"]

    assert get_min_requires("scikit-build-core", reqlist) is None
    assert get_min_requires("other", reqlist) is None


@pytest.mark.parametrize(
    ("spec", "version"),
    [
        ("==1.0", Version("1.0")),
        (">=1.0", Version("1.0")),
        (">1.0", Version("1.0")),
        ("~=1.0", Version("1.0")),
        (">=0.3,<0.4", Version("0.3")),
        ("", None),
    ],
)
def test_auto_requires_pkg_version(spec: str, version: Version):
    reqlist = [f"scikit_build_core{spec}"]
    assert get_min_requires("scikit-build-core", reqlist) == version


@pytest.mark.parametrize(
    ("expr", "answer"),
    [
        ("3.15", "3.15"),
        ("3.16", "3.16"),
        ("3.17.2", "3.17.2"),
        ("3.18...3.29", "3.18"),
        ("3.19.2...3.29", "3.19.2"),
    ],
)
def test_auto_cmake_version(expr: str, answer: str):
    txt = f"stuff()\ncmake_minimum_required(VERSION {expr})\nother()"
    res = find_min_cmake_version(txt)
    assert res == SpecifierSet(f">={answer}")
    txt = f"stuff()\n# cmake_minimum_version(VERSION 3.1)\ncmake_minimum_required(\nVERSION  {expr}  FATAL_ERROR)\nother()"
    res = find_min_cmake_version(txt)
    assert res == SpecifierSet(f">={answer}")
