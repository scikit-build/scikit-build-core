from __future__ import annotations

import shutil
import stat
import sys
from typing import TYPE_CHECKING

import pytest

from scikit_build_core._shutil import _fix_all_permissions

if TYPE_CHECKING:
    from pathlib import Path


def _make_dir_with_ro(tmp_path: Path) -> Path:
    base = tmp_path / "fix_all_perm"
    base.mkdir()
    base.joinpath("normal_file.txt").touch()
    ro = base / "read_only.txt"
    ro.touch()
    ro.chmod(stat.S_IREAD)
    nested = base / "nested"
    nested.mkdir()
    ro2 = nested / "read_only_2.txt"
    ro2.touch()
    ro2.chmod(stat.S_IREAD)

    # Validity check
    assert not stat.S_IMODE(ro2.stat().st_mode) & stat.S_IWRITE

    return base


@pytest.fixture
def make_dir_with_ro(tmp_path: Path) -> Path:
    return _make_dir_with_ro(tmp_path)


def test_broken_all_permissions(make_dir_with_ro: Path) -> None:
    if sys.platform.startswith("win"):
        with pytest.raises(PermissionError):
            shutil.rmtree(make_dir_with_ro)
    else:
        shutil.rmtree(make_dir_with_ro)


def test_fix_all_permissions(make_dir_with_ro: Path) -> None:
    _fix_all_permissions(str(make_dir_with_ro))
    shutil.rmtree(make_dir_with_ro)
