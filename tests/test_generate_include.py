import tarfile
import zipfile
from pathlib import Path

import pytest

from scikit_build_core.build import build_sdist, build_wheel

# Using [[tool.scikit-build.generate]] with `location = "source"` should
# automatically add the generated file to the sdist/wheel includes


@pytest.mark.parametrize("package", ["generate_include"], indirect=True)
@pytest.mark.usefixtures("package")
def test_generate_include_sdist(tmp_path: Path):
    dist = tmp_path / "dist"

    out = build_sdist(str(dist))
    sdist = dist / out

    with tarfile.open(sdist) as f:
        file_names = set(f.getnames())
        assert "generate_include-0.0.1/src/generate_include/_version.py" in file_names


@pytest.mark.parametrize("package", ["generate_include"], indirect=True)
@pytest.mark.usefixtures("package")
def test_generate_include_wheel(tmp_path: Path):
    dist = tmp_path / "dist"

    out = build_wheel(str(dist))
    wheel = dist / out

    with zipfile.ZipFile(wheel) as zf:
        file_names = set(zf.namelist())
        assert "generate_include/_version.py" in file_names
