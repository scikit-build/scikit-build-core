import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

import pytest

DIR = Path(__file__).parent.resolve()
HELLO_PEP518 = DIR / "packages/simple_setuptools_ext"


@pytest.mark.compile
@pytest.mark.configure
@pytest.mark.integration
def test_pep518_wheel(pep518, virtualenv):
    dist = HELLO_PEP518 / "dist"
    shutil.rmtree(dist, ignore_errors=True)

    subprocess.run(
        [sys.executable, "-m", "build", "--wheel"], cwd=HELLO_PEP518, check=True
    )
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

    virtualenv.run(f"python -m pip install {wheel}")

    version = virtualenv.run(
        'python -c "import cmake_example; print(cmake_example.__version__)"',
        capture=True,
    )
    assert version.strip() == "0.0.1"

    add = virtualenv.run(
        'python -c "import cmake_example; print(cmake_example.add(1, 2))"',
        capture=True,
    )
    assert add.strip() == "3"


@pytest.mark.compile
@pytest.mark.configure
@pytest.mark.integration
def test_pep518_pip(pep518, virtualenv):
    virtualenv.run(f"python -m pip install -v {HELLO_PEP518}")

    version = virtualenv.run(
        'python -c "import cmake_example; print(cmake_example.__version__)"',
        capture=True,
    )
    assert version.strip() == "0.0.1"

    add = virtualenv.run(
        'python -c "import cmake_example; print(cmake_example.add(1, 2))"',
        capture=True,
    )
    assert add.strip() == "3"
