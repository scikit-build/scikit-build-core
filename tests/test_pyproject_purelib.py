from pathlib import Path

import pytest

from scikit_build_core.build import build_wheel


@pytest.mark.compile
@pytest.mark.configure
@pytest.mark.parametrize("package", ["simple_purelib_package"], indirect=True)
@pytest.mark.usefixtures("package")
def test_pep517_wheel(virtualenv, tmp_path: Path):
    dist = tmp_path / "dist"
    out = build_wheel(str(dist), {})
    (wheel,) = dist.glob("purelib_example-0.0.1-*-none-any.whl")
    wheel = wheel.resolve()  # Windows mingw64 and UCRT now requires this
    assert wheel == dist / out

    virtualenv.install(wheel)

    version = virtualenv.execute(
        "import purelib_example; print(purelib_example.__version__)",
    )
    assert version.strip() == "1.2.3"
