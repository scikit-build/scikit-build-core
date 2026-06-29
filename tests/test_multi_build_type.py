from __future__ import annotations

import shutil
import zipfile
from pathlib import Path

import pytest
from packaging.specifiers import SpecifierSet

from scikit_build_core.build import build_editable, build_wheel
from scikit_build_core.program_search import best_program, get_cmake_programs

DIR = Path(__file__).parent.absolute()

has_ninja = shutil.which("ninja") is not None
# Ninja Multi-Config requires CMake 3.17+.
has_multi_config = (
    best_program(get_cmake_programs(), version=SpecifierSet(">=3.17")) is not None
)


@pytest.fixture(
    params=[
        None,
        pytest.param(
            "Ninja",
            marks=pytest.mark.skipif(not has_ninja, reason="ninja required"),
        ),
        pytest.param(
            "Ninja Multi-Config",
            marks=[
                pytest.mark.skipif(not has_ninja, reason="ninja required"),
                pytest.mark.skipif(
                    not has_multi_config,
                    reason="CMake 3.17+ required for Ninja Multi-Config",
                ),
            ],
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


def _read_cache_build_type(build_dir: Path) -> str:
    for line in (build_dir / "CMakeCache.txt").read_text().splitlines():
        if line.startswith("CMAKE_BUILD_TYPE:"):
            return line.split("=", 1)[1]
    return ""


@pytest.mark.configure
@pytest.mark.skipif(not has_ninja, reason="ninja required")
@pytest.mark.parametrize("package", ["multi_build_type"], indirect=True)
@pytest.mark.usefixtures("package")
def test_multi_build_type_editable_rebuild_restores_primary(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A single-config rebuild build dir is left on the primary build type.

    The redirect rebuild shim runs ``cmake --build`` without ``--config`` and was
    given the primary configuration's options, so the shared build directory must
    end configured for the primary type, not the last extra one.
    """
    monkeypatch.setenv("CMAKE_GENERATOR", "Ninja")
    build_dir = tmp_path / "build"
    dist = tmp_path / "dist"
    build_editable(
        str(dist),
        {"build-dir": str(build_dir), "editable.rebuild": "true"},
    )

    assert _read_cache_build_type(build_dir) == "Release"
