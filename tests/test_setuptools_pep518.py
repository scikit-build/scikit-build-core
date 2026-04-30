import sys
import zipfile
from pathlib import Path

import pytest
from conftest import enable_inplace_editable

from scikit_build_core.setuptools import build_meta as setuptools_build_meta

pytestmark = pytest.mark.setuptools
build_editable = getattr(setuptools_build_meta, "build_editable", None)


# TODO: work out why this fails on Cygwin
@pytest.mark.compile
@pytest.mark.configure
@pytest.mark.integration
@pytest.mark.broken_on_urct
@pytest.mark.xfail(
    sys.platform.startswith("cygwin"),
    reason="Cygwin fails here with ld errors",
    strict=False,
)
@pytest.mark.parametrize("package", ["simple_setuptools_ext"], indirect=True)
@pytest.mark.usefixtures("package", "pybind11")
def test_pep518_wheel(isolated, tmp_path: Path):
    dist = tmp_path / "dist"
    isolated.install("build[virtualenv]")
    isolated.module("build", "--wheel", f"--outdir={dist}")
    (wheel,) = dist.iterdir()
    assert "cmake_example-0.0.1" in wheel.name
    assert wheel.suffix == ".whl"

    with zipfile.ZipFile(wheel) as zf:
        file_names = {Path(n).parts[0] for n in zf.namelist()}

    assert len(file_names) == 2
    assert "cmake_example-0.0.1.dist-info" in file_names
    file_names.remove("cmake_example-0.0.1.dist-info")
    (so_file,) = file_names

    assert so_file.startswith("cmake_example")
    print("SOFILE:", so_file)

    isolated.install(wheel)

    version = isolated.execute("import cmake_example; print(cmake_example.__version__)")
    assert version == "0.0.1"

    add = isolated.execute("import cmake_example; print(cmake_example.add(1, 2))")
    assert add == "3"


@pytest.mark.compile
@pytest.mark.configure
@pytest.mark.integration
@pytest.mark.broken_on_urct
@pytest.mark.xfail(
    sys.platform.startswith("cygwin"),
    reason="Cygwin fails here with ld errors",
    strict=False,
)
@pytest.mark.parametrize("package", ["simple_setuptools_ext"], indirect=True)
@pytest.mark.usefixtures("package", "pybind11")
def test_pep518_pip(isolated):
    isolated.install("-v", ".")

    version = isolated.execute(
        "import cmake_example; print(cmake_example.__version__)",
    )
    assert version == "0.0.1"

    add = isolated.execute(
        "import cmake_example; print(cmake_example.add(1, 2))",
    )
    assert add == "3"


@pytest.mark.compile
@pytest.mark.configure
@pytest.mark.integration
@pytest.mark.broken_on_urct
@pytest.mark.xfail(
    sys.platform.startswith("cygwin"),
    reason="Cygwin fails here with ld errors",
    strict=False,
)
@pytest.mark.skipif(
    build_editable is None, reason="Requires setuptools editable support"
)
@pytest.mark.parametrize("package", ["simple_setuptools_ext"], indirect=True)
@pytest.mark.usefixtures("package", "pybind11")
def test_pep518_pip_editable(isolated):
    enable_inplace_editable()
    isolated.install("-v", "-e", ".")

    module_dir = isolated.execute(
        "import pathlib, cmake_example; print(pathlib.Path(cmake_example.__file__).resolve().parent)"
    )
    assert Path(module_dir) == Path("src").resolve()

    version = isolated.execute(
        "import cmake_example; print(cmake_example.__version__)",
    )
    assert version == "0.0.1"

    add = isolated.execute(
        "import cmake_example; print(cmake_example.add(1, 2))",
    )
    assert add == "3"
