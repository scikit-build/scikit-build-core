import shutil
import sys
import zipfile
from pathlib import Path

import pytest

from scikit_build_core.build import build_wheel

DIR = Path(__file__).parent.resolve()
ABI_PKG = DIR / "packages/abi3_pyproject_ext"


@pytest.mark.compile
@pytest.mark.configure
@pytest.mark.skipif(
    sys.implementation.name == "pypy", reason="pypy does not support abi3"
)
def test_abi3_wheel(tmp_path, monkeypatch, virtualenv):
    dist = tmp_path / "dist"
    dist.mkdir()
    monkeypatch.chdir(ABI_PKG)
    if Path("dist").is_dir():
        shutil.rmtree("dist")
    if Path("build").is_dir():
        shutil.rmtree("build")

    out = build_wheel(str(dist))
    (wheel,) = dist.glob("abi3_example-0.0.1-*.whl")
    assert wheel == dist / out
    assert "-cp37-abi3-" in out

    if sys.version_info >= (3, 8):
        with wheel.open("rb") as f:
            p = zipfile.Path(f)
            file_names = [p.name for p in p.iterdir()]

        assert len(file_names) == 2
        assert "abi3_example-0.0.1.dist-info" in file_names
        file_names.remove("abi3_example-0.0.1.dist-info")
        (so_file,) = file_names

        assert (
            so_file == "abi3_example.pyd"
            if sys.platform.startswith("win")
            else "abi3_example.abi3.so"
        )

    virtualenv.run(f"python -m pip install {wheel}")

    output = virtualenv.run(
        'python -c "import abi3_example; print(abi3_example.square(2))"',
        capture=True,
    )
    assert output.strip() == "4.0"
