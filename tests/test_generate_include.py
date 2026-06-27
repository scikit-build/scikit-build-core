import tarfile
import zipfile
from pathlib import Path

import pytest

from scikit_build_core.build import build_sdist, build_wheel

DIR = Path(__file__).parent.resolve()
SRC = DIR / "packages/generate_include"


@pytest.fixture
def cleanup_generated():
    version_file = SRC / "src/generate_include/_version.py"
    yield version_file
    version_file.unlink(missing_ok=True)


def test_generate_include_sdist(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, cleanup_generated: Path
):
    dist = tmp_path.resolve() / "dist"
    monkeypatch.chdir(SRC)

    out = build_sdist(str(dist))
    sdist = dist / out
    assert cleanup_generated.is_file()

    with tarfile.open(sdist) as f:
        file_names = set(f.getnames())
        assert "generate_include-0.0.1/src/generate_include/_version.py" in file_names


def test_generate_include_wheel(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, cleanup_generated: Path
):
    dist = tmp_path.resolve() / "dist"
    monkeypatch.chdir(SRC)

    out = build_wheel(str(dist))
    wheel = dist / out
    assert cleanup_generated.is_file()

    with zipfile.ZipFile(wheel) as zf:
        file_names = set(zf.namelist())
        assert "generate_include/_version.py" in file_names
