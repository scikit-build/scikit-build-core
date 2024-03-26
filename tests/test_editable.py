import ast
import shutil
import sys
from pathlib import Path

import pytest
from conftest import PackageInfo, process_package


@pytest.mark.compile()
@pytest.mark.configure()
@pytest.mark.integration()
@pytest.mark.parametrize("isolate", [True, False], ids=["isolated", "notisolated"])
@pytest.mark.parametrize(
    "package",
    [
        pytest.param(
            True,
            id="package",
            marks=[pytest.mark.xfail(reason="Only data folders supported currently")],
        ),
        pytest.param(False, id="datafolder"),
    ],
)
@pytest.mark.usefixtures("navigate_editable")
@pytest.mark.xfail(
    sys.version_info[:2] == (3, 9), reason="Python 3.9 not supported yet"
)
def test_navigate_editable(isolated, isolate, package):
    isolate_args = ["--no-build-isolation"] if not isolate else []
    isolated.install("pip>=23")
    if not isolate:
        isolated.install("scikit-build-core[pyproject]")

    if package:
        init_py = Path("python/shared_pkg/data/__init__.py")
        init_py.touch()

    isolated.install(
        "-v", "--config-settings=build-dir=build/{wheel_tag}", *isolate_args, "-e", "."
    )

    value = isolated.execute("import shared_pkg; shared_pkg.call_c_method()")
    assert value == "c_method"

    value = isolated.execute("import shared_pkg; shared_pkg.call_py_method()")
    assert value == "py_method"

    value = isolated.execute("import shared_pkg; shared_pkg.read_py_data_txt()")
    assert value == "Some_value_Py"

    value = isolated.execute("import shared_pkg; shared_pkg.read_c_generated_txt()")
    assert value == "Some_value_C"


@pytest.mark.compile()
@pytest.mark.configure()
@pytest.mark.integration()
@pytest.mark.parametrize(
    ("editable", "editable_mode"), [(False, ""), (True, "redirect"), (True, "inplace")]
)
def test_cython_pxd(monkeypatch, tmp_path, editable, editable_mode, isolated):
    editable_flag = ["-e"] if editable else []

    config_mode_flags = []
    if editable:
        config_mode_flags.append(f"--config-settings=editable.mode={editable_mode}")
    if editable_mode != "inplace":
        config_mode_flags.append("--config-settings=build-dir=build/{wheel_tag}")

    package1 = PackageInfo(
        "cython_pxd_editable/pkg1",
    )
    tmp_path1 = tmp_path / "pkg1"
    tmp_path1.mkdir()
    process_package(package1, tmp_path1, monkeypatch)

    isolated.install("pip>23", "cython", "scikit-build-core[pyproject]")

    isolated.install(
        "-v",
        *config_mode_flags,
        "--no-build-isolation",
        *editable_flag,
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
        *config_mode_flags,
        "--no-build-isolation",
        *editable_flag,
        ".",
    )


@pytest.mark.compile()
@pytest.mark.configure()
@pytest.mark.integration()
def test_editable_symlink(monkeypatch, tmp_path, isolated):
    # The nested directory name here must be identical to the package name
    # (editable_symlink in this case) to trigger the undesired behavior.
    pkg_name = "editable_symlink"
    pkg = PackageInfo(pkg_name)
    package_dir = tmp_path / pkg_name

    # Need to set symlinks=True.
    shutil.copytree(
        Path(__file__).parent / "packages" / pkg.name, package_dir, symlinks=True
    )

    # Have to change to the `project` directory because above we use the top-level
    # directory `editable_symlink` in order to ensure that the symlinked VERSION file is
    # also present in the temporary directory.
    monkeypatch.chdir(package_dir / "project")

    isolated.install("pip>23", "pybind11", "scikit-build-core[pyproject]")

    isolated.install(
        "-v",
        "--no-build-isolation",
        "-e",
        ".",
    )

    value = isolated.execute(f"import {pkg_name}; print({pkg_name}.__path__)")
    value = ast.literal_eval(value)
    assert len(value) == 1
