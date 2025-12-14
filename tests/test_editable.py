from __future__ import annotations

import platform
import sys
import textwrap
from pathlib import Path

import pytest
from conftest import PackageInfo, process_package


@pytest.mark.compile
@pytest.mark.configure
@pytest.mark.integration
@pytest.mark.parametrize(
    "py_pkg",
    [
        pytest.param(
            True,
            id="package",
            marks=[pytest.mark.xfail(reason="Only data folders supported currently")],
        ),
        pytest.param(False, id="datafolder"),
    ],
)
@pytest.mark.parametrize("package", {"navigate_editable"}, indirect=True)
@pytest.mark.usefixtures("package")
@pytest.mark.xfail(
    sys.version_info[:2] == (3, 9), reason="Python 3.9 not supported yet"
)
def test_navigate_editable(isolated, isolate, py_pkg):
    if py_pkg:
        init_py = Path("python/shared_pkg/data/__init__.py")
        init_py.touch()

    isolated.install(
        "-v", "--config-settings=build-dir=build/{wheel_tag}", *isolate.flags, "-e", "."
    )

    value = isolated.execute("import shared_pkg; shared_pkg.call_c_method()")
    assert value == "c_method"

    value = isolated.execute("import shared_pkg; shared_pkg.call_py_method()")
    assert value == "py_method"

    value = isolated.execute("import shared_pkg; shared_pkg.read_py_data_txt()")
    assert value == "Some_value_Py"

    value = isolated.execute("import shared_pkg; shared_pkg.read_c_generated_txt()")
    assert value == "Some_value_C"


@pytest.mark.compile
@pytest.mark.configure
@pytest.mark.integration
@pytest.mark.parametrize("isolate", {False}, indirect=True)
def test_cython_pxd(monkeypatch, tmp_path, editable, isolated, isolate):
    isolated.install("cython")

    package1 = PackageInfo(
        "cython_pxd_editable/pkg1",
    )
    tmp_path1 = tmp_path / "pkg1"
    tmp_path1.mkdir()
    process_package(package1, tmp_path1, monkeypatch)

    isolated.install(
        "-v",
        *isolate.flags,
        *editable.flags,
        ".",
    )

    package2 = PackageInfo(
        "cython_pxd_editable/pkg2",
    )
    tmp_path2 = tmp_path / "pkg2"
    tmp_path2.mkdir()
    process_package(package2, tmp_path2, monkeypatch)

    isolated.install(
        "-v",
        *isolate.flags,
        *editable.flags,
        ".",
    )


@pytest.mark.compile
@pytest.mark.configure
@pytest.mark.integration
@pytest.mark.parametrize("package", {"simplest_c"}, indirect=True)
@pytest.mark.parametrize("isolate", {False}, indirect=True)
@pytest.mark.usefixtures("package")
def test_install_dir(isolated, isolate):
    settings_overrides = {
        "build-dir": "build/{wheel_tag}",
        "wheel.install-dir": "other_pkg",
        "editable.rebuild": "true",
    }
    # Create a dummy other_pkg package to satisfy the import
    other_pkg_src = Path("./src/other_pkg")
    other_pkg_src.joinpath("simplest").mkdir(parents=True)
    other_pkg_src.joinpath("__init__.py").write_text(
        textwrap.dedent(
            """
            from .simplest._module import square
            """
        )
    )
    other_pkg_src.joinpath("simplest/__init__.py").touch()

    isolated.install(
        "-v",
        *[f"--config-settings={k}={v}" for k, v in settings_overrides.items()],
        *isolate.flags,
        "-e",
        ".",
    )

    # Make sure the package is correctly installed in the subdirectory
    other_pkg_path = isolated.platlib / "other_pkg"
    c_module_glob = list(other_pkg_path.glob("simplest/_module*"))
    assert len(c_module_glob) == 1
    c_module = c_module_glob[0]
    assert c_module.exists()
    # If `install-dir` was not taken into account it would install here
    failed_c_module = other_pkg_path / "../simplest" / c_module.name
    assert not failed_c_module.exists()

    # Run an import in order to re-trigger the rebuild and check paths again
    out = isolated.execute("import other_pkg.simplest")
    assert "Running cmake" in out
    assert c_module.exists()
    assert not failed_c_module.exists()


@pytest.mark.compile
@pytest.mark.configure
@pytest.mark.integration
@pytest.mark.parametrize("package", {"importlib_editable"}, indirect=True)
@pytest.mark.usefixtures("package")
def test_direct_import(editable, isolated, monkeypatch, tmp_path):
    # TODO: Investigate these failures
    if platform.system() == "Windows" and editable.mode == "inplace":
        pytest.xfail("Windows fails to import the top-level extension module")

    isolated.install(
        "-v",
        *editable.flags,
        ".",
    )

    # Exit the package path before execution
    # TODO: Use src-layout instead
    monkeypatch.chdir(tmp_path)
    isolated.execute("import pkg")
    isolated.execute("import pmod")
    isolated.execute("import emod")


@pytest.mark.compile
@pytest.mark.configure
@pytest.mark.integration
@pytest.mark.parametrize("package", {"importlib_editable"}, indirect=True)
@pytest.mark.usefixtures("package")
def test_importlib_resources(editable, isolated, monkeypatch, tmp_path):
    if sys.version_info < (3, 9):
        pytest.skip("importlib.resources.files is introduced in Python 3.9")

    # TODO: Investigate these failures
    if editable.mode == "redirect":
        pytest.xfail("Redirect mode is at navigating importlib.resources.files")
    if platform.system() == "Windows" and editable.mode == "inplace":
        pytest.xfail("Windows fails to import the top-level extension module")

    isolated.install(
        "-v",
        *editable.flags,
        ".",
    )

    # Exit the package path before execution
    # TODO: Use src-layout instead
    monkeypatch.chdir(tmp_path)
    isolated.execute(
        textwrap.dedent(
            """
            from importlib import import_module
            from importlib.resources import files
            from pathlib import Path

            def is_extension(path):
                for ext in (".so", ".pyd"):
                    if ext in path.suffixes:
                        return True
                return False

            def check_pkg(pkg_name):
                try:
                    pkg = import_module(pkg_name)
                    pkg_root = files(pkg)
                    print(f"pkg_root: [{type(pkg_root)}] {pkg_root}")
                    pkg_files = list(pkg_root.iterdir())
                    for path in pkg_files:
                        print(f"path: [{type(path)}] {path}")
                    assert any(is_extension(path) for path in pkg_files if isinstance(path, Path))
                except Exception as err:
                    msg = f"Failed in {str(pkg)}"
                    raise RuntimeError(msg) from err

            check_pkg("pkg")
            check_pkg("pkg.sub_a")
            check_pkg("pkg.sub_b")
            check_pkg("pkg.sub_b.sub_c")
            check_pkg("pkg.sub_b.sub_d")
            """
        )
    )
