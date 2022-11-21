import shutil
import sys
import zipfile
from pathlib import Path

import numpy as np
import pytest

from scikit_build_core.build import build_wheel

DIR = Path(__file__).parent.resolve()
FORTRAN_EXAMPLE = DIR / "packages/fortran_example"


@pytest.mark.compile
@pytest.mark.configure
@pytest.mark.fortran
def test_pep517_wheel(tmp_path, monkeypatch, virtualenv):
    dist = tmp_path / "dist"
    dist.mkdir()
    monkeypatch.chdir(FORTRAN_EXAMPLE)
    if Path("dist").is_dir():
        shutil.rmtree("dist")
    out = build_wheel(str(dist))
    (wheel,) = dist.glob("fibby-0.0.1-*.whl")
    assert wheel == dist / out

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

    virtualenv.run(f"python -m pip install {wheel}")

    output = virtualenv.run(
        "python -c 'import fibby; import numpy as np; a = np.zeros(9); fibby.fib(a); print(a)'",
        capture=True,
    )

    assert output.strip() == str(np.array([0, 1, 1, 2, 3, 5, 8, 13, 21], dtype=float))
