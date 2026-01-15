"""Test regular and editable installs with generated files.

Illustrate the supported and correct ways to use generated files
(other than traditional compiled extension modules).

Check a variety of scenarios in which package files (modules or data) are
not present in the source tree to confirm that we can find resources as expected,
either by ``import`` or with tools such as `importlib.resources.files()`.
"""

from __future__ import annotations

import sys

import pytest


@pytest.mark.compile
@pytest.mark.configure
@pytest.mark.integration
@pytest.mark.parametrize("package", ["cmake_generated"], indirect=True)
@pytest.mark.skipif(
    sys.version_info < (3, 9),
    reason="importlib.resources.files is introduced in Python 3.9",
)
def test_basic_data_resources(editable, isolate, isolated, package):
    isolated.install(
        "-v",
        *editable.flags,
        ".",
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
@pytest.mark.parametrize("package", ["cmake_generated"], indirect=True)
@pytest.mark.skipif(
    sys.version_info < (3, 9),
    reason="importlib.resources.files is introduced in Python 3.9",
)
def test_configure_time_generated_data(editable, isolate, isolated, package):
    isolated.install(
        "-v",
        *editable.flags,
        ".",
    )
    value = isolated.execute(
        "import cmake_generated; print(cmake_generated.get_configured_data())"
    )
    assert value == "value written by cmake file generation"


@pytest.mark.compile
@pytest.mark.configure
@pytest.mark.integration
@pytest.mark.parametrize("package", ["cmake_generated"], indirect=True)
@pytest.mark.skipif(
    sys.version_info < (3, 9),
    reason="importlib.resources.files is introduced in Python 3.9",
)
def test_build_time_generated_data(editable, isolate, isolated, package):
    isolated.install(
        "-v",
        *editable.flags,
        ".",
    )
    value = isolated.execute(
        "import cmake_generated; print(cmake_generated.get_namespace_generated_data())"
    )
    assert value == "value written by cmake custom_command"


@pytest.mark.compile
@pytest.mark.configure
@pytest.mark.integration
@pytest.mark.parametrize("package", ["cmake_generated"], indirect=True)
@pytest.mark.skipif(
    sys.version_info < (3, 9),
    reason="importlib.resources.files is introduced in Python 3.9",
)
def test_compiled_ctypes_resource(editable, isolate, isolated, package):
    isolated.install(
        "-v",
        *editable.flags,
        ".",
    )
    value = isolated.execute(
        "import cmake_generated; print(cmake_generated.ctypes_function()())"
    )
    assert value == str(42)


@pytest.mark.compile
@pytest.mark.configure
@pytest.mark.integration
@pytest.mark.parametrize("package", ["cmake_generated"], indirect=True)
@pytest.mark.skipif(
    sys.version_info < (3, 9),
    reason="importlib.resources.files is introduced in Python 3.9",
)
def test_configure_time_generated_module(editable, isolate, isolated, package):
    isolated.install(
        "-v",
        *editable.flags,
        ".",
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
@pytest.mark.parametrize("package", ["cmake_generated"], indirect=True)
@pytest.mark.skipif(
    sys.version_info < (3, 9),
    reason="importlib.resources.files is introduced in Python 3.9",
)
def test_build_time_generated_module(editable, isolate, isolated, package):
    isolated.install(
        "-v",
        *editable.flags,
        ".",
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
