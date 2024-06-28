import zipfile
from pathlib import Path

import pytest

from scikit_build_core.build import build_wheel
from scikit_build_core.errors import CMakeConfigError

from pathutils import contained


@pytest.mark.compile()
@pytest.mark.configure()
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

    with zipfile.ZipFile(wheel) as zf:
        file_paths = {Path(n) for n in zf.namelist()}
    data_paths = set(contained(file_paths, "cmake_dirs-0.0.1.data"))

    file_names = {p.parts[0] for p in file_paths}
    data_dir = {p.parts[0] for p in data_paths}
    package = {p.name for p in contained(file_paths, "cmake_dirs")}
    data = {p.name for p in contained(data_paths, "data")}
    headers = {p.name for p in contained(data_paths, "headers")}
    scripts = {p.name for p in contained(data_paths, "scripts")}

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
