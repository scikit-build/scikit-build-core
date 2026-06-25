from __future__ import annotations

import tarfile
import textwrap
import zipfile
from typing import TYPE_CHECKING

import pytest

from scikit_build_core.build import build_sdist, build_wheel

if TYPE_CHECKING:
    from collections.abc import Mapping
    from pathlib import Path

PYPROJECT = """\
[build-system]
requires = ["scikit-build-core"]
build-backend = "scikit_build_core.build"

[project]
name = "pkg"
version = "0.1.0"

[tool.scikit-build]
wheel.cmake = {cmake}
sdist.cmake = {cmake}
experimental = {experimental}
{extra}
"""


def make_pure_pkg(
    root: Path,
    extra: str = "",
    *,
    cmake: bool = False,
    experimental: bool = True,
) -> None:
    """Write a minimal package rooted at ``root`` (pure-Python by default)."""
    pkg = root / "pkg"
    pkg.mkdir(parents=True, exist_ok=True)
    (pkg / "__init__.py").write_text("__version__ = '0.1.0'\n")
    (root / "pyproject.toml").write_text(
        PYPROJECT.format(
            extra=extra,
            cmake=str(cmake).lower(),
            experimental=str(experimental).lower(),
        )
    )


def wheel_names(dist: Path) -> set[str]:
    (wheel,) = dist.glob("pkg-0.1.0-*.whl")
    with zipfile.ZipFile(wheel) as zf:
        return set(zf.namelist())


def wheel_read(dist: Path, arcname: str) -> bytes:
    (wheel,) = dist.glob("pkg-0.1.0-*.whl")
    with zipfile.ZipFile(wheel) as zf:
        return zf.read(arcname)


@pytest.fixture
def chdir_tmp(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Path:
    root = tmp_path / "proj"
    root.mkdir()
    monkeypatch.chdir(root)
    return root


def test_force_include_file_into_wheel(chdir_tmp: Path) -> None:
    make_pure_pkg(
        chdir_tmp,
        extra='force-include = {"extra/data.txt" = "pkg/data.txt"}',
    )
    (chdir_tmp / "extra").mkdir()
    (chdir_tmp / "extra" / "data.txt").write_text("hello")

    dist = chdir_tmp / "dist"
    build_wheel(str(dist), {})

    assert "pkg/data.txt" in wheel_names(dist)
    assert wheel_read(dist, "pkg/data.txt") == b"hello"


def test_force_include_directory_recurses_and_skips_junk(chdir_tmp: Path) -> None:
    make_pure_pkg(
        chdir_tmp,
        extra='force-include = {"assets" = "pkg/assets"}',
    )
    assets = chdir_tmp / "assets"
    (assets / "sub").mkdir(parents=True)
    (assets / "a.txt").write_text("a")
    (assets / "sub" / "b.txt").write_text("b")
    # Junk that must be skipped.
    (assets / "__pycache__").mkdir()
    (assets / "__pycache__" / "x.pyc").write_text("junk")
    (assets / "ignored.pyc").write_text("junk")

    dist = chdir_tmp / "dist"
    build_wheel(str(dist), {})

    names = wheel_names(dist)
    assert "pkg/assets/a.txt" in names
    assert "pkg/assets/sub/b.txt" in names
    assert not any("__pycache__" in n for n in names)
    assert not any(n.endswith(".pyc") for n in names)


def test_force_include_external_source(chdir_tmp: Path) -> None:
    make_pure_pkg(
        chdir_tmp,
        extra='force-include = {"../outside.txt" = "pkg/outside.txt"}',
    )
    (chdir_tmp.parent / "outside.txt").write_text("external")

    dist = chdir_tmp / "dist"
    build_wheel(str(dist), {})

    assert wheel_read(dist, "pkg/outside.txt") == b"external"


def test_force_include_leading_slash_targets_scripts(chdir_tmp: Path) -> None:
    make_pure_pkg(
        chdir_tmp,
        extra='force-include = {"run.sh" = {wheel = "/scripts/run.sh"}}',
    )
    (chdir_tmp / "run.sh").write_text("#!/bin/sh\n")

    dist = chdir_tmp / "dist"
    build_wheel(str(dist), {})

    assert "pkg-0.1.0.data/scripts/run.sh" in wheel_names(dist)


def test_force_include_leading_slash_requires_experimental(chdir_tmp: Path) -> None:
    make_pure_pkg(
        chdir_tmp,
        extra='force-include = {"run.sh" = {wheel = "/scripts/run.sh"}}',
        experimental=False,
    )
    (chdir_tmp / "run.sh").write_text("#!/bin/sh\n")

    dist = chdir_tmp / "dist"
    with pytest.raises(AssertionError, match=r"[Ee]xperimental"):
        build_wheel(str(dist), {})


@pytest.mark.parametrize("bad", ["/abs/escape.txt", "../escape.txt", "a/../../x"])
def test_force_include_rejects_escaping_sdist_dest(chdir_tmp: Path, bad: str) -> None:
    make_pure_pkg(
        chdir_tmp,
        extra=f'force-include = {{"blob.txt" = {{sdist = "{bad}"}}}}',
    )
    (chdir_tmp / "blob.txt").write_text("x")

    dist = chdir_tmp / "dist"
    with pytest.raises(AssertionError, match=r"relative path without"):
        build_sdist(str(dist), {})


def test_force_include_rejects_escaping_wheel_dest(chdir_tmp: Path) -> None:
    make_pure_pkg(
        chdir_tmp,
        extra='force-include = {"blob.txt" = "../escape.txt"}',
    )
    (chdir_tmp / "blob.txt").write_text("x")

    dist = chdir_tmp / "dist"
    with pytest.raises(AssertionError):
        build_wheel(str(dist), {})


def test_force_include_overrides_package_file(chdir_tmp: Path) -> None:
    make_pure_pkg(
        chdir_tmp,
        extra='force-include = {"override.py" = "pkg/__init__.py"}',
    )
    (chdir_tmp / "override.py").write_bytes(b"FORCED = True\n")

    dist = chdir_tmp / "dist"
    build_wheel(str(dist), {})

    assert wheel_read(dist, "pkg/__init__.py") == b"FORCED = True\n"


def test_force_include_missing_source_skipped(chdir_tmp: Path) -> None:
    make_pure_pkg(
        chdir_tmp,
        extra='force-include = {"does-not-exist.txt" = "pkg/missing.txt"}',
    )

    dist = chdir_tmp / "dist"
    build_wheel(str(dist), {})

    assert "pkg/missing.txt" not in wheel_names(dist)


def test_force_include_sdist_target(chdir_tmp: Path) -> None:
    make_pure_pkg(
        chdir_tmp,
        extra=(
            "force-include = {"
            '"vendor/blob.txt" = {sdist = "vendored/blob.txt"}, '
            '"wheel-only.txt" = "pkg/wheel_only.txt"}'
        ),
    )
    (chdir_tmp / "vendor").mkdir()
    (chdir_tmp / "vendor" / "blob.txt").write_text("vendored")
    (chdir_tmp / "wheel-only.txt").write_text("w")

    dist = chdir_tmp / "dist"
    build_sdist(str(dist), {})

    (sdist,) = dist.glob("pkg-0.1.0.tar.gz")
    with tarfile.open(sdist) as tf:
        names = set(tf.getnames())

    assert "pkg-0.1.0/vendored/blob.txt" in names
    # A bare string is wheel-only, so it must not appear in the SDist.
    assert not any("wheel_only" in n for n in names)


@pytest.mark.compile
@pytest.mark.configure
def test_force_include_build_target_visible_to_cmake(chdir_tmp: Path) -> None:
    """A {build=...} entry lands in the CMake build dir before configure."""
    make_pure_pkg(
        chdir_tmp,
        extra='force-include = {"injected.cmake" = {build = "injected.cmake"}}',
        cmake=True,
    )
    (chdir_tmp / "injected.cmake").write_text("set(INJECTED_OK TRUE)\n")
    (chdir_tmp / "CMakeLists.txt").write_text(
        textwrap.dedent("""\
        cmake_minimum_required(VERSION 3.15)
        project(pkg LANGUAGES NONE)
        if(NOT EXISTS "${CMAKE_BINARY_DIR}/injected.cmake")
          message(FATAL_ERROR "force-include build target missing")
        endif()
        include("${CMAKE_BINARY_DIR}/injected.cmake")
        if(NOT INJECTED_OK)
          message(FATAL_ERROR "injected.cmake did not run")
        endif()
        install(CODE "message(STATUS configured)")
        """)
    )

    dist = chdir_tmp / "dist"
    build_wheel(str(dist), {})
    # Build succeeds only if the injected file was present at configure time.
    assert list(dist.glob("pkg-0.1.0-*.whl"))


def _read_force_include(
    tmp_path: Path,
    toml: str = "",
    config_settings: dict[str, str] | None = None,
    env: dict[str, str] | None = None,
) -> Mapping[str, object]:
    import scikit_build_core.settings.skbuild_read_settings as rs

    pyproject_toml = tmp_path / "pyproject.toml"
    pyproject_toml.write_text(toml, encoding="utf-8")
    reader = rs.SettingsReader.from_file(
        pyproject_toml, config_settings or {}, env=env or {}
    )
    assert list(reader.unrecognized_options()) == []
    return reader.settings.force_include


def test_settings_force_include_toml_forms(tmp_path: Path) -> None:
    from scikit_build_core.settings.skbuild_model import ForceIncludeTargets

    fi = _read_force_include(
        tmp_path,
        toml=textwrap.dedent("""\
            [tool.scikit-build.force-include]
            "vendor/lib.so" = "pkg/_lib.so"
            "../data" = {sdist = "data", wheel = "pkg/data"}
            "toolchain.cmake" = {build = "toolchain.cmake"}
            """),
    )
    assert fi["vendor/lib.so"] == "pkg/_lib.so"
    assert fi["../data"] == ForceIncludeTargets(sdist="data", wheel="pkg/data")
    assert fi["toolchain.cmake"] == ForceIncludeTargets(build="toolchain.cmake")


def test_settings_force_include_envvar_bare_string(tmp_path: Path) -> None:
    fi = _read_force_include(
        tmp_path, env={"SKBUILD_FORCE_INCLUDE": "a.txt=pkg/a.txt;b.txt=pkg/b.txt"}
    )
    assert fi == {"a.txt": "pkg/a.txt", "b.txt": "pkg/b.txt"}


def test_settings_force_include_config_settings_bare_string(tmp_path: Path) -> None:
    fi = _read_force_include(
        tmp_path, config_settings={"force-include.c.txt": "pkg/c.txt"}
    )
    assert fi == {"c.txt": "pkg/c.txt"}
