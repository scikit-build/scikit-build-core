import sys
import zipfile
from pathlib import Path

import pytest

from scikit_build_core.build import build_wheel
from scikit_build_core.errors import CMakeConfigError


@pytest.mark.compile()
@pytest.mark.configure()
@pytest.mark.skipif(
    sys.version_info < (3, 8),
    reason="Python 3.7 doesn't have a nice Path zipfile interface",
)
@pytest.mark.usefixtures("package_filepath_pure")
def test_pep517_wheel_extra_dirs(monkeypatch):
    monkeypatch.setenv("SKBUILD_CMAKE_DEFINE", "SOME_DEFINE3=baz;SOME_DEFINE4=baz")
    monkeypatch.setenv("SKBUILD_CMAKE_ARGS", "-DSOME_ARGS1=baz")

    dist = Path("dist")
    out = build_wheel(
        "dist",
        {"cmake.define.SOME_DEFINE2": "bar", "cmake.define.SOME_DEFINE3": "bar"},
    )
    (wheel,) = dist.glob("cmake_dirs-0.0.1-*.whl")
    assert wheel == dist / out

    if sys.version_info >= (3, 8):
        with wheel.open("rb") as f:
            p = zipfile.Path(f)
            file_names = {p.name for p in p.iterdir()}
            data_dir = {p.name for p in p.joinpath("cmake_dirs-0.0.1.data").iterdir()}
            package = {p.name for p in p.joinpath("cmake_dirs").iterdir()}
            data = {p.name for p in p.joinpath("cmake_dirs-0.0.1.data/data").iterdir()}
            headers = {
                p.name for p in p.joinpath("cmake_dirs-0.0.1.data/headers").iterdir()
            }
            scripts = {
                p.name for p in p.joinpath("cmake_dirs-0.0.1.data/scripts").iterdir()
            }

        assert {
            "cmake_dirs-0.0.1.dist-info",
            "cmake_dirs-0.0.1.data",
            "cmake_dirs",
            "random_file.py",
        } == file_names

        assert data_dir == {"data", "headers", "scripts"}

        assert package == {"main.py"}
        assert data == {"in_data.txt"}
        assert headers == {"in_headers.h"}
        assert scripts == {"in_scripts.py"}


@pytest.mark.usefixtures("package_filepath_pure")
def test_pep517_wheel_too_old_core(monkeypatch):
    monkeypatch.setenv("SKBUILD_CMAKE_DEFINE", "SOME_DEFINE3=baz;SOME_DEFINE4=baz")
    monkeypatch.setenv("SKBUILD_CMAKE_ARGS", "-DSOME_ARGS1=baz")

    with pytest.raises(CMakeConfigError):
        build_wheel(
            "dist",
            {
                "cmake.define.SOME_DEFINE2": "bar",
                "cmake.define.SOME_DEFINE3": "bar",
                "minimum-version": "99",
            },
        )
