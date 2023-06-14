import shutil
import sys
import sysconfig
import zipfile
from pathlib import Path

import pytest
from packaging.version import Version

from scikit_build_core.build import build_wheel
from scikit_build_core.program_search import (
    best_program,
    get_cmake_programs,
    get_ninja_programs,
)

np = pytest.importorskip("numpy")

DIR = Path(__file__).parent.resolve()
FORTRAN_EXAMPLE = DIR / "packages/fortran_example"


cmake_info = best_program(get_cmake_programs(), minimum_version=Version("3.17.2"))
ninja_info = best_program(get_ninja_programs(), minimum_version=Version("1.10"))


@pytest.mark.compile()
@pytest.mark.configure()
@pytest.mark.fortran()
@pytest.mark.network()
@pytest.mark.skipif(shutil.which("gfortran") is None, reason="gfortran not available")
@pytest.mark.skipif(
    sysconfig.get_platform().startswith("win"),
    reason="No reasonable Fortran compiler for MSVC",
)
@pytest.mark.skipif(
    cmake_info is None, reason="CMake needs to be 3.17.2+ to support Fortran with Ninja"
)
@pytest.mark.skipif(
    ninja_info is None, reason="Ninja needs to be 1.10+ to support Fortran with CMake"
)
def test_pep517_wheel(tmp_path, monkeypatch, virtualenv):
    dist = tmp_path / "dist"
    dist.mkdir()
    monkeypatch.chdir(FORTRAN_EXAMPLE)
    if Path("dist").is_dir():
        shutil.rmtree("dist")
    out = build_wheel(str(dist))
    (wheel,) = dist.glob("fibby-0.0.1-*.whl")
    assert wheel == dist / out
    print(wheel)

    if sys.version_info >= (3, 8):
        with wheel.open("rb") as f:
            p = zipfile.Path(f)
            file_names = [p.name for p in p.iterdir()]

        assert len(file_names) == 2
        assert "fibby-0.0.1.dist-info" in file_names
        file_names.remove("fibby-0.0.1.dist-info")
        (so_file,) = file_names

        assert so_file.startswith("fibby")
        print("SOFILE:", so_file)

    virtualenv.install(wheel)

    output = virtualenv.execute(
        "import fibby; import numpy as np; a = np.zeros(9); fibby.fib(a); print(a)",
    )

    assert output == str(np.array([0, 1, 1, 2, 3, 5, 8, 13, 21], dtype=float))
