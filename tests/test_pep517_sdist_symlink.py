from __future__ import annotations

import tarfile
from pathlib import Path

import pytest

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
        pytest.param({}, "reg", id="dereference_default"),
        pytest.param({"sdist.resolve-symlinks": "false"}, "sym", id="no_dereference"),
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
