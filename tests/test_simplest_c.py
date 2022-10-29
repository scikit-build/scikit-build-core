import sys
from pathlib import Path

import pytest

from scikit_build_core.build import build_wheel

DIR = Path(__file__).parent.resolve()
SIMPLEST = DIR / "packages/simplest_c"


@pytest.mark.compile
@pytest.mark.configure
@pytest.mark.skipif(
    sys.implementation.name == "pypy",
    reason="PyPy reports the wrong SOABI (fixed upstream)",
)
def test_pep517_wheel(tmp_path, monkeypatch, virtualenv):
    dist = tmp_path / "dist"
    dist.mkdir()
    monkeypatch.chdir(SIMPLEST)
    out = build_wheel(str(dist))
    (wheel,) = dist.glob("scikit_build_simplest-0.0.1-*.whl")
    assert wheel == dist / out

    virtualenv.run(f"python -m pip install {wheel}")

    version = virtualenv.run(
        'python -c "from scikit_build_simplest import square; print(square(2))"',
        capture=True,
    )
    assert version.strip() == "4.0"
