from __future__ import annotations

import tarfile
from pathlib import Path

import pytest

from scikit_build_core._logging import rich_warning
from scikit_build_core.build import build_sdist


@pytest.fixture
def can_symlink(tmp_path: Path) -> None:
    """Skip the test if symlinks are not supported on this OS."""
    target = tmp_path / "target"
    target.touch()
    try:
        tmp_path.joinpath("link").symlink_to(target)
    except OSError:
        pytest.skip(
            "Creating symlinks is not supported/allowed on this OS without privileges"
        )


@pytest.mark.usefixtures("package_simple_pyproject_ext", "can_symlink")
@pytest.mark.parametrize(
    ("config_settings", "expected_type"),
    [
        pytest.param({}, "reg", id="resolve_all_default"),
        pytest.param({"sdist.resolve-symlinks": "none"}, "sym", id="resolve_none"),
    ],
)
def test_pep517_sdist_symlink(
    tmp_path: Path,
    config_settings: dict[str, list[str] | str],
    expected_type: str,
) -> None:
    Path("CMakeLists_link.txt").symlink_to("CMakeLists.txt")

    out = build_sdist(str(tmp_path), config_settings=config_settings or None)

    with tarfile.open(tmp_path / out, "r:gz") as tar:
        link_member = tar.getmember("cmake_example-0.0.1/CMakeLists_link.txt")
        if expected_type == "reg":
            assert link_member.isreg(), (
                "The symlink should have been stored as a regular file"
            )
        else:
            assert link_member.issym(), (
                "The symlink should have been stored as a symlink"
            )


@pytest.mark.usefixtures("package_simple_pyproject_ext", "can_symlink")
def test_pep517_sdist_dangling_symlink(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """
    A dangling symlink cannot be dereferenced; with the ``resolve-symlinks =
    "all"`` default the build must fall back to storing it as a symlink member
    instead of crashing (#1417).
    """
    Path("dangling_link.txt").symlink_to("does-not-exist.txt")

    rich_warning.cache_clear()
    out = build_sdist(str(tmp_path), config_settings=None)

    with tarfile.open(tmp_path / out, "r:gz") as tar:
        link_member = tar.getmember("cmake_example-0.0.1/dangling_link.txt")
        assert link_member.issym(), (
            "A dangling symlink should be stored as a symlink, not dereferenced"
        )

    err = capsys.readouterr().err
    assert "dangling_link.txt" in err
    assert "sdist.resolve-symlinks" in err
