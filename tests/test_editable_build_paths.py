"""Pure-Python (no-CMake) editable builds that exercise the rebuild-path guards.

These reach the wheel backend's editable code paths without needing CMake, so
they stay fast and hermetic while covering #1417 bugs B and C.
"""

from __future__ import annotations

import ast
import zipfile

import pytest

from scikit_build_core.build import build_editable

TYPE_CHECKING = False
if TYPE_CHECKING:
    from pathlib import Path

PYPROJECT = """\
[build-system]
requires = ["scikit-build-core"]
build-backend = "scikit_build_core.build"

[project]
name = "pkg"
version = "0.1.0"

[tool.scikit-build]
wheel.cmake = false
sdist.cmake = false
experimental = true
{extra}
"""


def make_pure_pkg(root: Path, extra: str = "") -> None:
    pkg = root / "pkg"
    pkg.mkdir(parents=True, exist_ok=True)
    (pkg / "__init__.py").write_text("__version__ = '0.1.0'\n")
    (root / "pyproject.toml").write_text(PYPROJECT.format(extra=extra))


def read_shim(dist: Path) -> str:
    (wheel,) = dist.glob("pkg-0.1.0-*.whl")
    with zipfile.ZipFile(wheel) as zf:
        return zf.read("_editable_skbc_pkg.py").decode()


@pytest.fixture
def chdir_tmp(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Path:
    root = tmp_path / "proj"
    root.mkdir()
    monkeypatch.chdir(root)
    return root


def test_editable_rebuild_nonplatlib_install_dir_friendly_error(
    chdir_tmp: Path,
) -> None:
    # #1417 Bug B: a rebuildable editable with a non-platlib wheel.install-dir
    # must raise the clear "non-platlib" guard, not a raw
    # ValueError('... does not start with ...') from relative_to().
    make_pure_pkg(
        chdir_tmp,
        extra=(
            "editable.rebuild = true\n"
            'build-dir = "build"\n'
            'wheel.install-dir = "${SKBUILD_DATA_DIR}/pkg"\n'
        ),
    )
    dist = chdir_tmp / "dist"
    with pytest.raises(AssertionError, match=r"non-platlib wheel\.install-dir"):
        build_editable(str(dist), {})


def test_editable_inplace_no_build_dir_bakes_none_path(chdir_tmp: Path) -> None:
    # #1417 Bug C: an inplace editable with no CMake and no persistent build-dir
    # must bake path=None (a real rebuild would recreate a deleted temp dir and
    # fail with a confusing CMake error). None makes rebuild() give the intended
    # friendly RuntimeError instead.
    make_pure_pkg(chdir_tmp, extra='editable.mode = "inplace"')
    dist = chdir_tmp / "dist"
    build_editable(str(dist), {})

    shim = read_shim(dist)
    # install_inplace args: known_packages, search_paths, path, rebuild,
    # verbose, build_options. The path (3rd) must be the None sentinel, not a
    # since-deleted temp build dir. Parse the call so the check does not depend
    # on the source paths' text (e.g. a /tmp build root on Linux).
    (call,) = [
        node.value
        for node in ast.parse(shim).body
        if isinstance(node, ast.Expr)
        and isinstance(node.value, ast.Call)
        and getattr(node.value.func, "id", None) == "install_inplace"
    ]
    path_arg = call.args[2]
    assert isinstance(path_arg, ast.Constant)
    assert path_arg.value is None
