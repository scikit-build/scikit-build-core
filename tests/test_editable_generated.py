"""Test regular and editable installs with generated files.

Illustrate the supported and correct ways to use generated files
(other than traditional compiled extension modules).

Check a variety of scenarios in which package files (modules or data) are
not present in the source tree to confirm that we can find resources as expected,
either by ``import`` or with tools such as `importlib.resources.files()`.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest
from conftest import PackageInfo, VEnv, process_package

def _setup_package_for_editable_layout_tests(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    editable: bool,
    editable_mode: str,
    build_isolation: bool,
    isolated: VEnv,
) -> None:
    editable_flag = ["-e"] if editable else []

    config_mode_flags = []
    if editable:
        config_mode_flags.append(f"--config-settings=editable.mode={editable_mode}")
    if editable_mode != "inplace":
        config_mode_flags.append("--config-settings=build-dir=build/{wheel_tag}")

    build_isolation_flags = []
    if not build_isolation:
        build_isolation_flags.append("--no-build-isolation")

    # Use a context so that we only change into the directory up until the point where
    # we run the editable install. We do not want to be in that directory when importing
    # to avoid importing the source directory instead of the installed package.
    with monkeypatch.context() as m:
        package = PackageInfo("cmake_generated")
        process_package(package, tmp_path, m)

        assert isolated.wheelhouse

        ninja = [
            "ninja"
            for f in isolated.wheelhouse.iterdir()
            if f.name.startswith("ninja-")
        ]
        cmake = [
            "cmake"
            for f in isolated.wheelhouse.iterdir()
            if f.name.startswith("cmake-")
        ]

        isolated.install("pip>23")
        isolated.install("scikit-build-core", *ninja, *cmake)

        isolated.install(
            "-v",
            *config_mode_flags,
            *build_isolation_flags,
            *editable_flag,
            ".",
        )


@pytest.mark.compile
@pytest.mark.configure
@pytest.mark.integration
@pytest.mark.parametrize(
    ("editable", "editable_mode"),
    [
        (False, ""),
        (True, "redirect"),
        (True, "inplace"),
    ],
)
@pytest.mark.parametrize(
    "build_isolation",
    [True, False],
)
@pytest.mark.skipif(sys.version_info < (3, 9), reason="importlib.resources.files is introduced in Python 3.9")
def test_basic_data_resources(monkeypatch, tmp_path, editable, editable_mode, build_isolation, isolated):
    _setup_package_for_editable_layout_tests(
        monkeypatch, tmp_path, editable, editable_mode, build_isolation, isolated
    )

    value = isolated.execute("import cmake_generated; print(cmake_generated.get_static_data())")
    assert value == "static value in top-level package"

    value = isolated.execute("import cmake_generated.nested1; print(cmake_generated.nested1.get_static_data())")
    assert value == "static value in subpackage 1"

    value = isolated.execute("import cmake_generated; print(cmake_generated.get_namespace_static_data())")
    assert value == "static value in namespace package"
