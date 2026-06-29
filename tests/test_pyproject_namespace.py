from pathlib import Path

import pytest

from scikit_build_core.build import build_wheel


@pytest.mark.compile
@pytest.mark.configure
@pytest.mark.parametrize("package", ["namespace_purelib_package"], indirect=True)
@pytest.mark.usefixtures("package")
def test_pep517_wheel_namespace_package(virtualenv, tmp_path: Path):
    # A PEP 420 namespace package ('myns.mypkg' at src/myns/mypkg) is discovered
    # automatically, without an explicit wheel.packages mapping (issue #682).
    dist = tmp_path / "dist"
    out = build_wheel(str(dist), {})
    (wheel,) = dist.glob("myns_mypkg-0.0.1-*-none-any.whl")
    wheel = wheel.resolve()  # Windows mingw64 and UCRT now requires this
    assert wheel == dist / out

    virtualenv.install(wheel)

    version = virtualenv.execute(
        "import myns.mypkg; print(myns.mypkg.__version__)",
    )
    assert version.strip() == "1.2.3"
