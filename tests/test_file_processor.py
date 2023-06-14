from __future__ import annotations

import sys
from pathlib import Path

import pytest

from scikit_build_core.build._file_processor import each_unignored_file


@pytest.mark.skipif(
    sys.version_info < (3, 8) and sys.platform.startswith("win"),
    reason="Python 3.8+ required for symlinks on Windows",
)
@pytest.mark.skipif(
    sys.implementation.name == "pypy" and sys.platform.startswith("win"),
    reason="PyPy on Windows does not support symlinks",
)
def test_on_each_with_symlink(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """
    Test that each_unignored_file() does not follow symlinks.
    """
    monkeypatch.chdir(tmp_path)
    # Set up a gitignore
    gitignore = Path(".gitignore")
    gitignore.write_text("/hidden_dir")
    # Create a directory with a symlink to a file in the same directory
    dir = Path("dir")
    dir.mkdir()
    file1 = dir / "file"
    file1.write_text("content")
    file2 = dir / "link"
    file2.symlink_to("file")
    hidden_dir = Path("hidden_dir")
    hidden_dir.mkdir()
    hidden_file = hidden_dir / "file2"
    hidden_file.write_text("content2")
    exposed_symlink = dir / "exposed_symlink"
    exposed_symlink.symlink_to("../hidden_dir")

    if (
        sys.platform.startswith("win")
        and not exposed_symlink.joinpath("file2").is_file()
    ):
        pytest.skip("Windows symlink support not available")

    # Test that each_unignored_file() follows the symlink
    assert sorted(each_unignored_file(Path("."))) == [
        gitignore,
        exposed_symlink / "file2",
        file1,
        file2,
    ]
