from __future__ import annotations

import tarfile
from pathlib import Path

import pytest

from scikit_build_core.build import build_sdist


@pytest.mark.usefixtures("package_simple_pyproject_ext")
def test_pep517_sdist_symlink(tmp_path: Path):
    # Attempt to create a symlink in the current working directory
    try:
        Path("CMakeLists_link.txt").symlink_to("CMakeLists.txt")
    except OSError:
        pytest.skip(
            "Creating symlinks is not supported/allowed on this OS without privileges"
        )

    out = build_sdist(str(tmp_path))

    with tarfile.open(tmp_path / out, "r:gz") as tar:
        # Check that the symlink file is actually dereferenced into a regular file
        link_member = tar.getmember("cmake_example-0.0.1/CMakeLists_link.txt")
        assert link_member.isreg(), (
            "The symlink should have been stored as a regular file"
        )


@pytest.mark.usefixtures("package_simple_pyproject_ext")
def test_pep517_sdist_symlink_no_dereference(tmp_path: Path):
    try:
        Path("CMakeLists_link_no_deref.txt").symlink_to("CMakeLists.txt")
    except OSError:
        pytest.skip(
            "Creating symlinks is not supported/allowed on this OS without privileges"
        )

    out = build_sdist(
        str(tmp_path),
        config_settings={"sdist.dereference": "False"},
    )

    with tarfile.open(tmp_path / out, "r:gz") as tar:
        # Check that the symlink file is actually NOT dereferenced
        link_member = tar.getmember("cmake_example-0.0.1/CMakeLists_link_no_deref.txt")
        assert link_member.issym(), "The symlink should have been stored as a symlink"
