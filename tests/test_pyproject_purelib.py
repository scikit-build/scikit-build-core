from pathlib import Path

import pytest

from scikit_build_core.build import build_wheel


@pytest.mark.compile()
@pytest.mark.configure()
@pytest.mark.usefixtures("package_simple_purelib_package")
def test_pep517_wheel(virtualenv):
    dist = Path("dist")
    out = build_wheel("dist", {})
    (wheel,) = dist.glob("purelib_example-0.0.1-*-none-any.whl")
    assert wheel == dist / out

    virtualenv.install(wheel)

    version = virtualenv.execute(
        "import purelib_example; print(purelib_example.__version__)",
    )
    assert version.strip() == "1.2.3"
