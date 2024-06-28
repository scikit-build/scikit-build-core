import shutil
import sys
import sysconfig
import zipfile
from pathlib import Path

import pytest

from scikit_build_core.build import build_wheel

DIR = Path(__file__).parent.resolve()
ABI_PKG = DIR / "packages/abi3_pyproject_ext"
SYSCONFIGPLAT = sysconfig.get_platform()


@pytest.mark.compile()
@pytest.mark.configure()
@pytest.mark.skipif(
    sysconfig.get_platform().startswith(("msys", "mingw")),
    reason="abi3 FindPython on MSYS/MinGW reports not found",
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
    abi3 = sys.implementation.name == "cpython" and not sysconfig.get_config_var(
        "Py_GIL_DISABLED"
    )

    if abi3:
        assert "-cp37-abi3-" in out
    else:
        assert "-cp37-abi3-" not in out

    with zipfile.ZipFile(wheel) as zf:
        file_names = {Path(n).parts[0] for n in zf.namelist()}

    assert len(file_names) == 2
    assert "abi3_example-0.0.1.dist-info" in file_names
    file_names.remove("abi3_example-0.0.1.dist-info")
    (so_file,) = file_names

    if sysconfig.get_platform().startswith("win"):
        if sys.implementation.name == "cpython":
            assert so_file == "abi3_example.pyd"
        else:
            assert so_file.endswith(".pyd")
    elif sys.platform.startswith("cygwin"):
        if abi3:
            assert so_file == "abi3_example.abi3.dll"
        else:
            assert so_file != "abi3_example.abi3.dll"
    elif abi3:
        assert so_file == "abi3_example.abi3.so"
    else:
        assert so_file != "abi3_example.abi3.so"

    virtualenv.install(wheel)

    output = virtualenv.execute(
        "import abi3_example; print(abi3_example.square(2))",
    )
    assert output.strip() == "4.0"
