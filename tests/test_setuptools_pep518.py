import shutil
import sys
import zipfile
from pathlib import Path

import pytest

pytestmark = pytest.mark.setuptools

DIR = Path(__file__).parent.resolve()
HELLO_PEP518 = DIR / "packages/simple_setuptools_ext"


# TODO: work out why this fails on Cygwin
@pytest.mark.compile
@pytest.mark.configure
@pytest.mark.integration
@pytest.mark.skipif(
    sys.platform.startswith("cygwin"), reason="Cygwin fails here with ld errors"
)
def test_pep518_wheel(monkeypatch, isolated):
    dist = HELLO_PEP518 / "dist"
    shutil.rmtree(dist, ignore_errors=True)
    monkeypatch.chdir(HELLO_PEP518)
    isolated.install("build[virtualenv]")
    isolated.module("build", "--wheel")
    (wheel,) = dist.iterdir()
    assert "cmake_example-0.0.1" in wheel.name
    assert wheel.suffix == ".whl"

    if sys.version_info >= (3, 8):
        with wheel.open("rb") as f:
            p = zipfile.Path(f)
            file_names = [p.name for p in p.iterdir()]

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
@pytest.mark.skipif(
    sys.platform.startswith("cygwin"), reason="Cygwin fails here with ld errors"
)
def test_pep518_pip(isolated):
    isolated.install("-v", HELLO_PEP518)

    version = isolated.execute(
        "import cmake_example; print(cmake_example.__version__)",
    )
    assert version == "0.0.1"

    add = isolated.execute(
        "import cmake_example; print(cmake_example.add(1, 2))",
    )
    assert add == "3"
