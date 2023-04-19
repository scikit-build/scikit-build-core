import shutil
import sys
import sysconfig
import zipfile
from pathlib import Path

import pytest

from scikit_build_core.setuptools.build_meta import build_wheel

pytestmark = pytest.mark.setuptools

DIR = Path(__file__).parent.resolve()
ABI_PKG = DIR / "packages/abi3_setuptools_ext"
SYSCONFIGPLAT = sysconfig.get_platform()


@pytest.mark.compile()
@pytest.mark.configure()
@pytest.mark.skipif(
    sys.implementation.name == "pypy", reason="pypy does not support abi3"
)
@pytest.mark.skipif(
    SYSCONFIGPLAT.startswith(("msys", "mingw")),
    reason="abi3 FindPython on MSYS/MinGW reports not found",
)
def test_abi3_wheel(tmp_path, monkeypatch, virtualenv):
    dist = tmp_path / "dist"
    dist.mkdir()

    # create a temporary copy of the package source so we don't contaminate the
    # main source tree with build artefacts
    src = tmp_path / "src"
    shutil.copytree(ABI_PKG, src)
    monkeypatch.chdir(src)
    if Path("dist").is_dir():
        shutil.rmtree("dist")

    out = build_wheel(str(dist))
    (wheel,) = dist.glob("abi3_example-0.0.1-*.whl")
    assert wheel == dist / out
    assert "-cp37-abi3-" in out

    assert virtualenv.execute("print('hello')") == "hello"

    if sys.version_info >= (3, 8):
        with wheel.open("rb") as f:
            p = zipfile.Path(f)
            file_names = {p.name for p in p.iterdir()}

        if sysconfig.get_platform().startswith("win"):
            assert "abi3_example.pyd" in file_names
        elif sys.platform.startswith("cygwin"):
            assert "abi3_example.abi3.dll" in file_names
        else:
            assert "abi3_example.abi3.so" in file_names

    virtualenv.install(wheel)

    output = virtualenv.execute("import abi3_example; print(abi3_example.square(2))")
    assert output == "4.0"
