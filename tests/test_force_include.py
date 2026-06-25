from __future__ import annotations

import tarfile
import textwrap
import zipfile
from typing import TYPE_CHECKING

import pytest

from scikit_build_core.build import (
    build_editable,
    build_sdist,
    build_wheel,
    prepare_metadata_for_build_wheel,
)

if TYPE_CHECKING:
    from pathlib import Path

    from scikit_build_core.settings.skbuild_model import ScikitBuildSettings

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
        extra='wheel.force-include = {"extra/data.txt" = "pkg/data.txt"}',
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
        extra='wheel.force-include = {"assets" = "pkg/assets"}',
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
        extra='wheel.force-include = {"../outside.txt" = "pkg/outside.txt"}',
    )
    (chdir_tmp.parent / "outside.txt").write_text("external")

    dist = chdir_tmp / "dist"
    build_wheel(str(dist), {})

    assert wheel_read(dist, "pkg/outside.txt") == b"external"


def test_force_include_leading_slash_targets_scripts(chdir_tmp: Path) -> None:
    make_pure_pkg(
        chdir_tmp,
        extra='wheel.force-include = {"run.sh" = "/scripts/run.sh"}',
    )
    (chdir_tmp / "run.sh").write_text("#!/bin/sh\n")

    dist = chdir_tmp / "dist"
    build_wheel(str(dist), {})

    assert "pkg-0.1.0.data/scripts/run.sh" in wheel_names(dist)


def test_force_include_script_shebang_normalized(chdir_tmp: Path) -> None:
    """A force-included script's python shebang is normalized to #!python."""
    make_pure_pkg(
        chdir_tmp,
        extra='wheel.force-include = {"run.py" = "/scripts/run.py"}',
    )
    (chdir_tmp / "run.py").write_text("#!/usr/bin/env python\nprint('hi')\n")

    dist = chdir_tmp / "dist"
    build_wheel(str(dist), {})

    content = wheel_read(dist, "pkg-0.1.0.data/scripts/run.py")
    assert content.startswith(b"#!python\n")


def test_force_include_metadata_in_prepare(chdir_tmp: Path) -> None:
    """A force-included metadata file appears in prepared metadata and the wheel."""
    make_pure_pkg(
        chdir_tmp,
        extra='wheel.force-include = {"extra.txt" = "/metadata/extra/extra.txt"}',
    )
    (chdir_tmp / "extra.txt").write_text("meta")

    metadata_dir = chdir_tmp / "meta"
    metadata_dir.mkdir()
    dist_info = prepare_metadata_for_build_wheel(str(metadata_dir), {})
    prepared = metadata_dir / dist_info / "extra" / "extra.txt"
    assert prepared.read_text() == "meta"

    # Building with that metadata_directory must not raise on a mismatch.
    dist = chdir_tmp / "dist"
    build_wheel(str(dist), {}, str(metadata_dir / dist_info))
    assert "pkg-0.1.0.dist-info/extra/extra.txt" in wheel_names(dist)


def test_force_include_leading_slash_requires_experimental(chdir_tmp: Path) -> None:
    make_pure_pkg(
        chdir_tmp,
        extra='wheel.force-include = {"run.sh" = "/scripts/run.sh"}',
        experimental=False,
    )
    (chdir_tmp / "run.sh").write_text("#!/bin/sh\n")

    dist = chdir_tmp / "dist"
    with pytest.raises(AssertionError, match=r"[Ee]xperimental"):
        build_wheel(str(dist), {})


@pytest.mark.parametrize(
    "bad",
    [
        "/abs/escape.txt",
        "../escape.txt",
        "a/../../x",
        "C:/escape.txt",
        "..\\escape.txt",
    ],
)
def test_force_include_rejects_escaping_sdist_dest(chdir_tmp: Path, bad: str) -> None:
    bad_toml = bad.replace("\\", "\\\\")  # escape backslashes for the TOML string
    make_pure_pkg(
        chdir_tmp,
        extra=f'sdist.force-include = {{"blob.txt" = "{bad_toml}"}}',
    )
    (chdir_tmp / "blob.txt").write_text("x")

    dist = chdir_tmp / "dist"
    with pytest.raises(AssertionError, match=r"relative path without"):
        build_sdist(str(dist), {})


def test_force_include_rejects_escaping_wheel_dest(chdir_tmp: Path) -> None:
    make_pure_pkg(
        chdir_tmp,
        extra='wheel.force-include = {"blob.txt" = "../escape.txt"}',
    )
    (chdir_tmp / "blob.txt").write_text("x")

    dist = chdir_tmp / "dist"
    with pytest.raises(AssertionError):
        build_wheel(str(dist), {})


def test_force_include_overrides_package_file(chdir_tmp: Path) -> None:
    make_pure_pkg(
        chdir_tmp,
        extra='wheel.force-include = {"override.py" = "pkg/__init__.py"}',
    )
    (chdir_tmp / "override.py").write_bytes(b"FORCED = True\n")

    dist = chdir_tmp / "dist"
    build_wheel(str(dist), {})

    assert wheel_read(dist, "pkg/__init__.py") == b"FORCED = True\n"


def test_force_include_missing_sdist_source_errors(chdir_tmp: Path) -> None:
    make_pure_pkg(
        chdir_tmp,
        extra='sdist.force-include = {"does-not-exist.txt" = "missing.txt"}',
    )

    dist = chdir_tmp / "dist"
    with pytest.raises(FileNotFoundError, match=r"does-not-exist\.txt"):
        build_sdist(str(dist), {})


def test_force_include_missing_wheel_source_errors(chdir_tmp: Path) -> None:
    make_pure_pkg(
        chdir_tmp,
        extra='wheel.force-include = {"does-not-exist.txt" = "pkg/missing.txt"}',
    )

    dist = chdir_tmp / "dist"
    with pytest.raises(FileNotFoundError, match=r"does-not-exist\.txt"):
        build_wheel(str(dist), {})


def test_force_include_from_sdist_via_overrides(chdir_tmp: Path) -> None:
    """The documented overrides recipe redirects the wheel source when from-sdist."""
    make_pure_pkg(
        chdir_tmp,
        extra=textwrap.dedent("""\
            [tool.scikit-build.sdist.force-include]
            "../outside.txt" = "vendored/blob.txt"

            [[tool.scikit-build.overrides]]
            if.from-sdist = false
            wheel.force-include."../outside.txt" = "pkg/blob.txt"

            [[tool.scikit-build.overrides]]
            if.from-sdist = true
            wheel.force-include."vendored/blob.txt" = "pkg/blob.txt"
            """),
    )
    # Simulate an unpacked SDist: a PKG-INFO at the root, the original external
    # source gone, but the vendored copy present at the sdist destination.
    (chdir_tmp / "PKG-INFO").write_text("Metadata-Version: 2.1\nName: pkg\n")
    (chdir_tmp / "vendored").mkdir()
    (chdir_tmp / "vendored" / "blob.txt").write_text("vendored")

    dist = chdir_tmp / "dist"
    build_wheel(str(dist), {})

    assert wheel_read(dist, "pkg/blob.txt") == b"vendored"


def test_force_include_survives_wheel_exclude(chdir_tmp: Path) -> None:
    """A force-included file overrides a matching wheel.exclude pattern."""
    make_pure_pkg(
        chdir_tmp,
        extra=(
            'wheel.exclude = ["pkg/data.txt"]\n'
            'wheel.force-include = {"data.txt" = "pkg/data.txt"}'
        ),
    )
    (chdir_tmp / "data.txt").write_text("forced")

    dist = chdir_tmp / "dist"
    build_wheel(str(dist), {})

    assert "pkg/data.txt" in wheel_names(dist)
    assert wheel_read(dist, "pkg/data.txt") == b"forced"


def test_force_include_directory_respects_wheel_exclude(chdir_tmp: Path) -> None:
    """A force-included directory's members are still filtered by wheel.exclude."""
    make_pure_pkg(
        chdir_tmp,
        extra=(
            'wheel.exclude = ["pkg/assets/*.tmp"]\n'
            'wheel.force-include = {"assets" = "pkg/assets"}'
        ),
    )
    assets = chdir_tmp / "assets"
    assets.mkdir()
    (assets / "keep.txt").write_text("keep")
    (assets / "drop.tmp").write_text("drop")

    dist = chdir_tmp / "dist"
    build_wheel(str(dist), {})

    names = wheel_names(dist)
    assert "pkg/assets/keep.txt" in names
    # A directory copy is bulk, so exclude still trims it.
    assert "pkg/assets/drop.tmp" not in names


def test_force_include_pure_wheel_platlib_tree(chdir_tmp: Path) -> None:
    """A documented /platlib destination resolves to purelib on a pure wheel."""
    make_pure_pkg(
        chdir_tmp,
        extra='wheel.force-include = {"extra.txt" = "/platlib/pkg/extra.txt"}',
    )
    (chdir_tmp / "extra.txt").write_text("x")

    dist = chdir_tmp / "dist"
    build_wheel(str(dist), {})

    assert "pkg/extra.txt" in wheel_names(dist)


def test_force_include_sdist_directory_reproducible(chdir_tmp: Path) -> None:
    """Forced directory entries are ordered deterministically in the SDist tar."""
    make_pure_pkg(
        chdir_tmp,
        extra='sdist.force-include = {"assets" = "vendored"}',
    )
    assets = chdir_tmp / "assets"
    (assets / "sub").mkdir(parents=True)
    for name in ("c.txt", "a.txt", "b.txt"):
        (assets / name).write_text(name)
    (assets / "sub" / "z.txt").write_text("z")

    dist = chdir_tmp / "dist"
    build_sdist(str(dist), {})

    (sdist,) = dist.glob("pkg-0.1.0.tar.gz")
    with tarfile.open(sdist) as tf:
        forced = [n for n in tf.getnames() if "/vendored/" in n]

    assert forced == sorted(forced)


def test_force_include_into_editable_wheel(chdir_tmp: Path) -> None:
    """Wheel-target force-includes are baked into the editable wheel (not redirected)."""
    make_pure_pkg(
        chdir_tmp,
        extra='wheel.force-include = {"extra/data.txt" = "pkg/data.txt"}',
    )
    (chdir_tmp / "extra").mkdir()
    (chdir_tmp / "extra" / "data.txt").write_text("hello")

    dist = chdir_tmp / "dist"
    build_editable(str(dist), {})

    assert "pkg/data.txt" in wheel_names(dist)
    assert wheel_read(dist, "pkg/data.txt") == b"hello"


def test_force_include_editable_script_shebang_normalized(chdir_tmp: Path) -> None:
    """A force-included script's shebang is normalized in an editable wheel too."""
    make_pure_pkg(
        chdir_tmp,
        extra='wheel.force-include = {"run.py" = "/scripts/run.py"}',
    )
    (chdir_tmp / "run.py").write_text("#!/usr/bin/env python\nprint('hi')\n")

    dist = chdir_tmp / "dist"
    build_editable(str(dist), {})

    content = wheel_read(dist, "pkg-0.1.0.data/scripts/run.py")
    assert content.startswith(b"#!python\n")


def test_force_include_sdist_target(chdir_tmp: Path) -> None:
    make_pure_pkg(
        chdir_tmp,
        extra=(
            'sdist.force-include = {"vendor/blob.txt" = "vendored/blob.txt"}\n'
            'wheel.force-include = {"wheel-only.txt" = "pkg/wheel_only.txt"}'
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
    # A wheel-only entry must not appear in the SDist.
    assert not any("wheel_only" in n for n in names)


def _read_settings(
    tmp_path: Path,
    toml: str = "",
    config_settings: dict[str, str] | None = None,
    env: dict[str, str] | None = None,
) -> ScikitBuildSettings:
    import scikit_build_core.settings.skbuild_read_settings as rs

    pyproject_toml = tmp_path / "pyproject.toml"
    pyproject_toml.write_text(toml, encoding="utf-8")
    reader = rs.SettingsReader.from_file(
        pyproject_toml, config_settings or {}, env=env or {}
    )
    assert list(reader.unrecognized_options()) == []
    return reader.settings


def test_settings_force_include_toml(tmp_path: Path) -> None:
    settings = _read_settings(
        tmp_path,
        toml=textwrap.dedent("""\
            [tool.scikit-build.sdist.force-include]
            "vendor/data" = "data"

            [tool.scikit-build.wheel.force-include]
            "vendor/lib.so" = "pkg/_lib.so"
            "tools/run.sh" = "/scripts/run.sh"
            """),
    )
    assert settings.sdist.force_include == {"vendor/data": "data"}
    assert settings.wheel.force_include == {
        "vendor/lib.so": "pkg/_lib.so",
        "tools/run.sh": "/scripts/run.sh",
    }


def test_settings_force_include_envvar(tmp_path: Path) -> None:
    settings = _read_settings(
        tmp_path,
        env={
            "SKBUILD_SDIST_FORCE_INCLUDE": "a.txt=data/a.txt",
            "SKBUILD_WHEEL_FORCE_INCLUDE": "b.so=pkg/b.so;c.so=pkg/c.so",
        },
    )
    assert settings.sdist.force_include == {"a.txt": "data/a.txt"}
    assert settings.wheel.force_include == {"b.so": "pkg/b.so", "c.so": "pkg/c.so"}


def test_settings_force_include_config_settings(tmp_path: Path) -> None:
    settings = _read_settings(
        tmp_path,
        config_settings={
            "sdist.force-include.a.txt": "data/a.txt",
            "wheel.force-include.b.so": "pkg/b.so",
        },
    )
    assert settings.sdist.force_include == {"a.txt": "data/a.txt"}
    assert settings.wheel.force_include == {"b.so": "pkg/b.so"}
