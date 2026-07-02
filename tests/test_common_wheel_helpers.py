from __future__ import annotations

from pathlib import Path

import pytest

from scikit_build_core.build.common_wheel_helpers import (
    get_build_dir,
    get_install_dir,
    get_targetlib,
    get_wheel_tag,
    prepare_wheel_dirs,
)
from scikit_build_core.settings.skbuild_model import ScikitBuildSettings

WHEEL_SUBDIRS = {"data", "headers", "scripts", "null", "metadata"}


def _install_dir(tmp_path: Path, settings: ScikitBuildSettings) -> Path:
    targetlib = get_targetlib(settings)
    wheel_dirs = prepare_wheel_dirs(tmp_path / "wheel", targetlib=targetlib)
    return get_install_dir(settings, wheel_dirs=wheel_dirs, targetlib=targetlib)


def test_targetlib_platlib_by_default() -> None:
    assert get_targetlib(ScikitBuildSettings()) == "platlib"


def test_targetlib_purelib_when_cmake_disabled() -> None:
    settings = ScikitBuildSettings()
    settings.wheel.cmake = False
    assert get_targetlib(settings) == "purelib"


def test_targetlib_honors_explicit_platlib() -> None:
    settings = ScikitBuildSettings()
    settings.wheel.platlib = False
    assert get_targetlib(settings) == "purelib"


def test_purelib_tag_is_any() -> None:
    tags = get_wheel_tag(ScikitBuildSettings(), targetlib="purelib")
    assert tags.arch == "any"


def test_platlib_layout_created(tmp_path: Path) -> None:
    wheel_dirs = prepare_wheel_dirs(tmp_path / "wheel", targetlib="platlib")

    assert set(wheel_dirs) == {"platlib", *WHEEL_SUBDIRS}
    for d in wheel_dirs.values():
        assert d.is_dir()


def test_install_dir_defaults_to_targetlib(tmp_path: Path) -> None:
    settings = ScikitBuildSettings()
    wheel_dirs = prepare_wheel_dirs(tmp_path / "wheel", targetlib="platlib")
    install_dir = get_install_dir(settings, wheel_dirs=wheel_dirs, targetlib="platlib")

    assert install_dir == wheel_dirs["platlib"]


def test_install_dir_rejects_dotdot(tmp_path: Path) -> None:
    settings = ScikitBuildSettings()
    settings.wheel.install_dir = "../escape"

    with pytest.raises(AssertionError, match="must not contain"):
        _install_dir(tmp_path, settings)


def test_absolute_install_dir_requires_experimental(tmp_path: Path) -> None:
    settings = ScikitBuildSettings()
    settings.wheel.install_dir = "/data/foo"

    with pytest.raises(AssertionError, match="Experimental"):
        _install_dir(tmp_path, settings)


def test_absolute_install_dir_targets_wheel_subdir(tmp_path: Path) -> None:
    settings = ScikitBuildSettings()
    settings.experimental = True
    settings.wheel.install_dir = "/data/foo"

    assert _install_dir(tmp_path, settings) == tmp_path / "wheel" / "data" / "foo"


def test_absolute_install_dir_rejects_unknown_subdir(tmp_path: Path) -> None:
    settings = ScikitBuildSettings()
    settings.experimental = True
    settings.wheel.install_dir = "/nonsense/foo"

    with pytest.raises(AssertionError, match="valid wheel directory"):
        _install_dir(tmp_path, settings)


def _build_dir(
    tmp_path: Path, settings: ScikitBuildSettings, *, name: str = "pkg"
) -> Path:
    tags = get_wheel_tag(settings, targetlib="platlib")
    return get_build_dir(
        settings,
        tags=tags,
        state="wheel",
        editable=False,
        has_cmake=True,
        fallback=tmp_path / "build",
        name=name,
    )


def test_build_dir_fallback(tmp_path: Path) -> None:
    assert _build_dir(tmp_path, ScikitBuildSettings()) == tmp_path / "build"


def test_build_dir_explicit(tmp_path: Path) -> None:
    settings = ScikitBuildSettings()
    settings.build_dir = "custom-build"

    assert _build_dir(tmp_path, settings) == Path("custom-build")


def test_build_dir_name_placeholder(tmp_path: Path) -> None:
    # A shared build-dir setting (e.g. across a uv/hatch workspace) is
    # disambiguated per-project with {name}.
    settings = ScikitBuildSettings()
    settings.build_dir = "build/{name}"

    assert _build_dir(tmp_path, settings, name="my_pkg") == Path("build/my_pkg")


def test_build_dir_inplace_editable_uses_source_dir(tmp_path: Path) -> None:
    settings = ScikitBuildSettings()
    settings.editable.mode = "inplace"
    settings.cmake.source_dir = tmp_path / "src"

    tags = get_wheel_tag(settings, targetlib="platlib")
    build_dir = get_build_dir(
        settings,
        tags=tags,
        state="editable",
        editable=True,
        has_cmake=True,
        fallback=tmp_path / "build",
        name="pkg",
    )

    assert build_dir == tmp_path / "src"
