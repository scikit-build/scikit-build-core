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
@pytest.mark.skipif(
    sys.version_info < (3, 9),
    reason="importlib.resources.files is introduced in Python 3.9",
)
def test_basic_data_resources(
    monkeypatch, tmp_path, editable, editable_mode, build_isolation, isolated
):
    _setup_package_for_editable_layout_tests(
        monkeypatch, tmp_path, editable, editable_mode, build_isolation, isolated
    )

    value = isolated.execute(
        "import cmake_generated; print(cmake_generated.get_static_data())"
    )
    assert value == "static value in top-level package"

    value = isolated.execute(
        "import cmake_generated.nested1; print(cmake_generated.nested1.get_static_data())"
    )
    assert value == "static value in subpackage 1"

    value = isolated.execute(
        "import cmake_generated; print(cmake_generated.get_namespace_static_data())"
    )
    assert value == "static value in namespace package"


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
@pytest.mark.skipif(
    sys.version_info < (3, 9),
    reason="importlib.resources.files is introduced in Python 3.9",
)
def test_configure_time_generated_data(
    monkeypatch, tmp_path, editable, editable_mode, build_isolation, isolated
):
    _setup_package_for_editable_layout_tests(
        monkeypatch, tmp_path, editable, editable_mode, build_isolation, isolated
    )

    value = isolated.execute(
        "import cmake_generated; print(cmake_generated.get_configured_data())"
    )
    assert value == "value written by cmake file generation"


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
@pytest.mark.skipif(
    sys.version_info < (3, 9),
    reason="importlib.resources.files is introduced in Python 3.9",
)
def test_build_time_generated_data(
    monkeypatch, tmp_path, editable, editable_mode, build_isolation, isolated
):
    _setup_package_for_editable_layout_tests(
        monkeypatch, tmp_path, editable, editable_mode, build_isolation, isolated
    )

    value = isolated.execute(
        "import cmake_generated; print(cmake_generated.get_namespace_generated_data())"
    )
    assert value == "value written by cmake custom_command"


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
@pytest.mark.skipif(
    sys.version_info < (3, 9),
    reason="importlib.resources.files is introduced in Python 3.9",
)
def test_compiled_ctypes_resource(
    monkeypatch, tmp_path, editable, editable_mode, build_isolation, isolated
):
    _setup_package_for_editable_layout_tests(
        monkeypatch, tmp_path, editable, editable_mode, build_isolation, isolated
    )

    value = isolated.execute(
        "import cmake_generated; print(cmake_generated.ctypes_function()())"
    )
    assert value == str(42)


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
@pytest.mark.skipif(
    sys.version_info < (3, 9),
    reason="importlib.resources.files is introduced in Python 3.9",
)
def test_configure_time_generated_module(
    monkeypatch, tmp_path, editable, editable_mode, build_isolation, isolated
):
    _setup_package_for_editable_layout_tests(
        monkeypatch, tmp_path, editable, editable_mode, build_isolation, isolated
    )
    # Check that a generated module can access and be accessed by all parts of the package

    value = isolated.execute(
        "from cmake_generated.nested1.generated import __version__; print(__version__)"
    )
    assert value == "1.2.3"

    value = isolated.execute(
        "from cmake_generated.nested1.generated import cmake_generated_static_data; print(cmake_generated_static_data())"
    )
    assert value == "static value in top-level package"

    value = isolated.execute(
        "from cmake_generated.nested1.generated import cmake_generated_nested_static_data; print(cmake_generated_nested_static_data())"
    )
    assert value == "static value in subpackage 1"

    value = isolated.execute(
        "from cmake_generated.nested1.generated import cmake_generated_namespace_generated_data; print(cmake_generated_namespace_generated_data())"
    )
    assert value == "value written by cmake custom_command"

    value = isolated.execute(
        "from cmake_generated.nested1.generated import nested_data; print(nested_data)"
    )
    assert value == "success"
    value = isolated.execute(
        "from cmake_generated.nested1.generated import nested2_check; print(nested2_check())"
    )
    assert value == "success"
    value = isolated.execute(
        "from cmake_generated.nested2 import nested1_generated_check; print(nested1_generated_check())"
    )
    assert value == "success"


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
@pytest.mark.skipif(
    sys.version_info < (3, 9),
    reason="importlib.resources.files is introduced in Python 3.9",
)
def test_build_time_generated_module(
    monkeypatch, tmp_path, editable, editable_mode, build_isolation, isolated
):
    _setup_package_for_editable_layout_tests(
        monkeypatch, tmp_path, editable, editable_mode, build_isolation, isolated
    )
    # Check generated _version module
    attr_value = isolated.execute(
        "import cmake_generated; print(cmake_generated.__version__)"
    )
    assert attr_value == "1.2.3"
    metadata_value = isolated.execute(
        "import importlib.metadata; print(importlib.metadata.version('cmake_generated'))"
    )
    assert metadata_value == "1.2.3"
