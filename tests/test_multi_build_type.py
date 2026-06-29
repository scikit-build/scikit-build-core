from __future__ import annotations

import shutil
import zipfile
from pathlib import Path

import pytest

from scikit_build_core.build import build_wheel

DIR = Path(__file__).parent.absolute()

has_ninja = shutil.which("ninja") is not None


@pytest.fixture(
    params=[
        None,
        pytest.param(
            "Ninja",
            marks=pytest.mark.skipif(not has_ninja, reason="ninja required"),
        ),
        pytest.param(
            "Ninja Multi-Config",
            marks=pytest.mark.skipif(not has_ninja, reason="ninja required"),
        ),
    ]
)
def generator(
    request: pytest.FixtureRequest, monkeypatch: pytest.MonkeyPatch
) -> str | None:
    if request.param is None:
        monkeypatch.delenv("CMAKE_GENERATOR", raising=False)
    else:
        monkeypatch.setenv("CMAKE_GENERATOR", request.param)
    return request.param  # type: ignore[no-any-return]


@pytest.mark.configure
@pytest.mark.parametrize("package", ["multi_build_type"], indirect=True)
@pytest.mark.usefixtures("package", "generator")
def test_multi_build_type_wheel(tmp_path: Path) -> None:
    """A list cmake.build-type installs every configuration into one wheel."""
    dist = tmp_path / "dist"
    out = build_wheel(str(dist), {})
    wheel = (dist / out).resolve()

    with zipfile.ZipFile(wheel) as zf:
        names = set(zf.namelist())

    # Both the Release and Debug configurations should be installed.
    assert "multi_build_type/Release/marker.txt" in names
    assert "multi_build_type/Debug/marker.txt" in names


@pytest.mark.configure
@pytest.mark.parametrize("package", ["multi_build_type"], indirect=True)
@pytest.mark.usefixtures("package")
def test_multi_build_type_override_single(tmp_path: Path) -> None:
    """A single build type passed via config-settings overrides the list."""
    dist = tmp_path / "dist"
    out = build_wheel(str(dist), {"cmake.build-type": "Release"})
    wheel = (dist / out).resolve()

    with zipfile.ZipFile(wheel) as zf:
        names = set(zf.namelist())

    assert "multi_build_type/Release/marker.txt" in names
    assert "multi_build_type/Debug/marker.txt" not in names
