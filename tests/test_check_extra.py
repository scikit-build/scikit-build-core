from __future__ import annotations

import textwrap
from typing import TYPE_CHECKING

import pytest

from scikit_build_core._check_extra import _has_extra, warn_missing_extra

if TYPE_CHECKING:
    from pathlib import Path

    from pytest import CaptureFixture


@pytest.mark.parametrize(
    ("reqlist", "extra", "expected"),
    [
        (["scikit-build-core[setuptools]"], "setuptools", True),
        (["scikit_build_core[Setuptools]>=1"], "setuptools", True),
        (['scikit-build-core[setuptools]; python_version>="3"'], "setuptools", True),
        (["scikit-build-core[hatchling]"], "hatchling", True),
        (["scikit-build-core", "setuptools"], "setuptools", False),
        (["scikit-build-core[hatchling]"], "setuptools", False),
        (['scikit-build-core[setuptools]; python_version<"3"'], "setuptools", False),
        (["not a requirement!!", "scikit-build-core[setuptools]"], "setuptools", True),
        ([], "setuptools", False),
    ],
)
def test_has_extra(reqlist: list[str], extra: str, expected: bool) -> None:
    assert _has_extra(reqlist, extra) is expected


def _write_pyproject(tmp_path: Path, requires: str) -> Path:
    path = tmp_path / "pyproject.toml"
    path.write_text(
        textwrap.dedent(f"""\
            [build-system]
            requires = {requires}
            build-backend = "setuptools.build_meta"
            """)
    )
    return path


def test_warn_missing_extra_warns(tmp_path: Path, capsys: CaptureFixture[str]) -> None:
    path = _write_pyproject(tmp_path, '["scikit-build-core", "setuptools"]')
    warn_missing_extra("setuptools", pyproject_path=path)
    err = capsys.readouterr().err
    assert "scikit-build-core[setuptools]" in err
    assert "build-system.requires" in err


def test_warn_missing_extra_quiet(tmp_path: Path, capsys: CaptureFixture[str]) -> None:
    path = _write_pyproject(tmp_path, '["scikit-build-core[setuptools]"]')
    warn_missing_extra("setuptools", pyproject_path=path)
    assert capsys.readouterr().err == ""


def test_warn_missing_extra_no_pyproject(
    tmp_path: Path, capsys: CaptureFixture[str]
) -> None:
    warn_missing_extra("setuptools", pyproject_path=tmp_path / "pyproject.toml")
    assert capsys.readouterr().err == ""
