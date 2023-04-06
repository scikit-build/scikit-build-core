import sys
import zipfile
from pathlib import Path

import pytest

from scikit_build_core.build import build_editable


# TODO: figure out why gmake is reporting no rule to make simple_pure.cpp
@pytest.mark.compile()
@pytest.mark.configure()
@pytest.mark.xfail(
    sys.platform.startswith("cygwin"),
    strict=False,
    reason="No idea why this fails on Cygwin",
)
@pytest.mark.usefixtures("package_simplest_c")
def test_pep660_wheel():
    dist = Path("dist")
    out = build_editable("dist")
    (wheel,) = dist.glob("simplest-0.0.1-*.whl")
    assert wheel == dist / out

    if sys.version_info >= (3, 8):
        with wheel.open("rb") as f:
            p = zipfile.Path(f)
            file_names = [p.name for p in p.iterdir()]
            metadata = p.joinpath("simplest-0.0.1.dist-info/METADATA").read_text()

        assert len(file_names) == 4
        assert "simplest-0.0.1.dist-info" in file_names
        assert "simplest" in file_names
        assert "_simplest_editable.py" in file_names
        assert "_simplest_editable.pth" in file_names

        assert "Metadata-Version: 2.1" in metadata
        assert "Name: simplest" in metadata
        assert "Version: 0.0.1" in metadata


@pytest.mark.compile()
@pytest.mark.configure()
@pytest.mark.integration()
@pytest.mark.parametrize("isolate", [True, False])
@pytest.mark.usefixtures("package_simplest_c")
def test_pep660_pip_isolated(isolated, isolate):
    isolate_args = ["--no-build-isolation"] if not isolate else []
    isolated.install("pip>=23")
    if not isolate:
        isolated.install("scikit-build-core[pyproject]")

    isolated.install(
        "-v", "--config-settings=build-dir=build/{wheel_tag}", *isolate_args, "-e", "."
    )

    value = isolated.execute("import simplest; print(simplest.square(2))")
    assert value == "4.0"

    location = isolated.execute("import simplest; print(*simplest.__path__)")
    assert location == str(Path.cwd() / "src/simplest")

    location = isolated.execute("import simplest; print(simplest.__file__)")
    assert location == str(Path.cwd() / "src/simplest/__init__.py")
