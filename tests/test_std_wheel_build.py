from __future__ import annotations

from pathlib import Path

import pytest

from scikit_build_core.build.std_wheel_build import prepare_wheel_dirs
from scikit_build_core.settings.skbuild_model import ScikitBuildSettings

WHEEL_SUBDIRS = {"data", "headers", "scripts", "null", "metadata"}


def _layout(tmp_path: Path, settings: ScikitBuildSettings, **kwargs):
    wheel_root = tmp_path / "wheel"
    return prepare_wheel_dirs(
        settings=settings,
        wheel_root=wheel_root,
        build_tmp_folder=tmp_path,
        state="wheel",
        editable=False,
        has_cmake=True,
        **kwargs,
    )


def test_platlib_layout_created(tmp_path: Path) -> None:
    layout = _layout(tmp_path, ScikitBuildSettings())

    assert layout.targetlib == "platlib"
    assert set(layout.wheel_dirs) == {"platlib", *WHEEL_SUBDIRS}
    for d in layout.wheel_dirs.values():
        assert d.is_dir()
    assert layout.install_dir == layout.wheel_dirs["platlib"]
    assert layout.build_dir == tmp_path / "build"


def test_purelib_when_cmake_disabled(tmp_path: Path) -> None:
    settings = ScikitBuildSettings()
    settings.wheel.cmake = False

    layout = prepare_wheel_dirs(
        settings=settings,
        wheel_root=tmp_path / "wheel",
        build_tmp_folder=tmp_path,
        state="wheel",
        editable=False,
        has_cmake=False,
    )

    assert layout.targetlib == "purelib"
    assert layout.tags.arch == "any"


def test_install_dir_rejects_dotdot(tmp_path: Path) -> None:
    settings = ScikitBuildSettings()
    settings.wheel.install_dir = "../escape"

    with pytest.raises(AssertionError, match="must not contain"):
        _layout(tmp_path, settings)


def test_absolute_install_dir_requires_experimental(tmp_path: Path) -> None:
    settings = ScikitBuildSettings()
    settings.wheel.install_dir = "/data/foo"

    with pytest.raises(AssertionError, match="Experimental"):
        _layout(tmp_path, settings)


def test_absolute_install_dir_targets_wheel_subdir(tmp_path: Path) -> None:
    settings = ScikitBuildSettings()
    settings.experimental = True
    settings.wheel.install_dir = "/data/foo"

    layout = _layout(tmp_path, settings)

    assert layout.install_dir == tmp_path / "wheel" / "data" / "foo"


def test_absolute_install_dir_rejects_unknown_subdir(tmp_path: Path) -> None:
    settings = ScikitBuildSettings()
    settings.experimental = True
    settings.wheel.install_dir = "/nonsense/foo"

    with pytest.raises(AssertionError, match="valid wheel directory"):
        _layout(tmp_path, settings)


def test_inplace_editable_uses_source_dir(tmp_path: Path) -> None:
    settings = ScikitBuildSettings()
    settings.editable.mode = "inplace"
    settings.cmake.source_dir = tmp_path / "src"

    layout = prepare_wheel_dirs(
        settings=settings,
        wheel_root=tmp_path / "wheel",
        build_tmp_folder=tmp_path,
        state="editable",
        editable=True,
        has_cmake=True,
    )

    assert layout.build_dir == tmp_path / "src"


def test_explicit_build_dir(tmp_path: Path) -> None:
    settings = ScikitBuildSettings()
    settings.build_dir = "custom-build"

    layout = _layout(tmp_path, settings)

    assert layout.build_dir == Path("custom-build")
