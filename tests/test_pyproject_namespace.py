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


@pytest.mark.integration
@pytest.mark.parametrize("editable_mode", ["redirect", "inplace"])
@pytest.mark.parametrize(
    "multiple_packages",
    [["namespace_purelib_package", "namespace_sibling_package"]],
    indirect=True,
)
def test_editable_namespace_sibling_distribution(
    multiple_packages, isolated, editable_mode
):
    # An editable install must not hide sibling distributions sharing the same
    # PEP 420 namespace (issue #1482): 'myns.otherpkg' (hatchling, installed
    # normally) must stay importable next to editable 'myns.mypkg'
    # (scikit-build-core). Neither package compiles anything.
    editable_pkg, sibling_pkg = multiple_packages

    isolated.install(str(sibling_pkg.workdir), installer="pip")
    isolated.install(
        "-v",
        f"--config-settings=editable.mode={editable_mode}",
        "-e",
        str(editable_pkg.workdir),
        installer="pip",
    )

    output = isolated.execute(
        "import myns.mypkg, myns.otherpkg;"
        " print(myns.mypkg.__version__, myns.otherpkg.value)"
    )
    assert output.strip() == "1.2.3 sibling"
