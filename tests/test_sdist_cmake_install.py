from __future__ import annotations

import logging
import shutil
import tarfile
import zipfile
from pathlib import Path

import pytest

from scikit_build_core.build import build_sdist, build_wheel

DIR = Path(__file__).parent.resolve()
PKG = DIR / "packages" / "sdist_cmake_install"

# The sdist build runs a real configure+build+install.
pytestmark = pytest.mark.configure


@pytest.fixture
def src(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    root = tmp_path / "src"
    shutil.copytree(PKG, root)
    monkeypatch.chdir(root)
    return root


def _build_sdist(dist: Path) -> Path:
    name = build_sdist(str(dist), {})
    return dist / name


def _extract(sdist: Path, dest: Path) -> None:
    with tarfile.open(sdist) as tar:
        try:
            tar.extractall(dest, filter="data")
        except TypeError:
            # Python without the extractall filter kwarg (no warning there either).
            tar.extractall(dest)  # noqa: S202


def test_sdist_cmake_install_vendors_install_tree(src: Path) -> None:
    """sdist.install-dir captures the staged install tree into the sdist."""
    dist = src / "dist"
    sdist = _build_sdist(dist)

    with tarfile.open(sdist) as tar:
        names = set(tar.getnames())
        config = tar.extractfile(
            "sdist_cmake_install-0.2.0/.cmake-install/purelib/sdist_cmake_install/cmake/example-config.cmake"
        )
        assert config is not None
        config_text = config.read().decode()

    assert {
        "sdist_cmake_install-0.2.0/.cmake-install/purelib/sdist_cmake_install/include/example.h",
        "sdist_cmake_install-0.2.0/.cmake-install/purelib/sdist_cmake_install/cmake/example-config.cmake",
        # A tree outside the install prefix (headers) is captured too.
        "sdist_cmake_install-0.2.0/.cmake-install/headers/example.h",
        # The original sources are still shipped too.
        "sdist_cmake_install-0.2.0/CMakeLists.txt",
        "sdist_cmake_install-0.2.0/pyproject.toml",
    } <= names
    # The configure-time substitution was captured (proves install, not just configure).
    assert 'set(EXAMPLE_VERSION "0.2.0")' in config_text
    # The install pass runs as a "wheel" build (its output becomes the wheel),
    # so if.state = "wheel" overrides and SKBUILD_STATE checks apply.
    assert 'set(EXAMPLE_STATE "wheel")' in config_text


def test_wheel_from_sdist_needs_no_cmake(
    src: Path,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capfd: pytest.CaptureFixture[str],
) -> None:
    """A wheel built from the unpacked sdist repackages the vendored tree, no CMake."""
    dist = src / "dist"
    sdist = _build_sdist(dist)

    unpacked = tmp_path / "unpacked"
    _extract(sdist, unpacked)
    sdist_root = unpacked / "sdist_cmake_install-0.2.0"
    assert (sdist_root / "PKG-INFO").is_file()  # triggers if.from-sdist
    monkeypatch.chdir(sdist_root)

    capfd.readouterr()  # drop the sdist-build output
    wheel_dir = tmp_path / "wheel"
    wheel_dir.mkdir()
    wheel_name = build_wheel(str(wheel_dir), {})

    out, _ = capfd.readouterr()
    assert "(wheel)" in out
    # wheel.cmake = false under if.from-sdist: CMake is never configured.
    assert "Configuring CMake" not in out
    assert "using" not in out  # the "using CMake <ver>" banner is absent

    # No CMake means a pure wheel.
    assert wheel_name.endswith("-py3-none-any.whl")

    with zipfile.ZipFile(wheel_dir / wheel_name) as zf:
        names = set(zf.namelist())
        config_text = zf.read("sdist_cmake_install/cmake/example-config.cmake").decode()

    assert "sdist_cmake_install/include/example.h" in names
    assert "sdist_cmake_install/cmake/example-config.cmake" in names
    # The headers tree (outside the install prefix) made it through too.
    assert any(n.endswith(".data/headers/example.h") for n in names)
    # The vendored, version-stamped config -- only reproducible if CMake had run
    # during the sdist build, not now.
    assert 'set(EXAMPLE_VERSION "0.2.0")' in config_text


def test_wheel_from_sdist_matches_direct_cmake_build(
    src: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The no-CMake from-sdist wheel matches a direct CMake build, file-for-file."""
    # Direct build from the source tree (no PKG-INFO -> CMake runs).
    direct_dir = src / "direct"
    direct_dir.mkdir()
    direct_name = build_wheel(str(direct_dir), {})
    with zipfile.ZipFile(direct_dir / direct_name) as zf:
        direct_names = {n for n in zf.namelist() if not n.endswith("RECORD")}

    # Build from the unpacked sdist (PKG-INFO -> no CMake).
    dist = src / "dist"
    sdist = _build_sdist(dist)
    unpacked = tmp_path / "unpacked"
    _extract(sdist, unpacked)
    monkeypatch.chdir(unpacked / "sdist_cmake_install-0.2.0")
    fromsdist_dir = tmp_path / "fromsdist"
    fromsdist_dir.mkdir()
    fromsdist_name = build_wheel(str(fromsdist_dir), {})
    with zipfile.ZipFile(fromsdist_dir / fromsdist_name) as zf:
        fromsdist_names = {n for n in zf.namelist() if not n.endswith("RECORD")}

    assert direct_name == fromsdist_name
    assert direct_names == fromsdist_names


def test_install_dir_without_cmake_warns(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    """sdist.install-dir without sdist.cmake = true is a no-op, with a warning."""
    root = tmp_path / "pkg"
    (root / "pkg").mkdir(parents=True)
    (root / "pkg" / "__init__.py").write_text("")
    (root / "pyproject.toml").write_text(
        "[build-system]\n"
        'requires = ["scikit-build-core"]\n'
        'build-backend = "scikit_build_core.build"\n\n'
        "[project]\n"
        'name = "pkg"\n'
        'version = "0.1.0"\n\n'
        "[tool.scikit-build]\n"
        'sdist.install-dir = ".cmake-install"\n'  # but sdist.cmake left false
    )
    monkeypatch.chdir(root)

    caplog.set_level(logging.WARNING)
    dist = root / "dist"
    name = build_sdist(str(dist), {})

    assert any(
        "install-dir is set but sdist.cmake" in str(r.msg) for r in caplog.records
    )
    with tarfile.open(dist / name) as tar:
        assert not any(".cmake-install" in n for n in tar.getnames())
