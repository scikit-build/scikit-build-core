from __future__ import annotations

import sys
from pathlib import Path

import pytest

from scikit_build_core.build._file_processor import each_unignored_file


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

    local_ignored_file = Path("local_ignored_file.txt")
    Path(".git/info").mkdir(parents=True)
    Path(".git/info/exclude").write_text(f"{local_ignored_file}\n")

    nested_dir = Path("nested_dir")
    nested_dir.mkdir()
    nested_dir.joinpath("not_ignored.txt").write_text("content")
    nested_dir.joinpath("ignored.txt").write_text("content")
    nested_dir.joinpath(".gitignore").write_text("ignored.txt")
    nested_dir.joinpath("more").mkdir()
    nested_dir.joinpath("more/ignored.txt").write_text("content")

    if (
        sys.platform.startswith("win")
        and not exposed_symlink.joinpath("file2").is_file()
    ):
        pytest.skip("Windows symlink support not available")

    # Test that each_unignored_file() follows the symlink
    assert set(each_unignored_file(Path())) == {
        gitignore,
        exposed_symlink / "file2",
        file1,
        file2,
        nested_dir / "not_ignored.txt",
        nested_dir / ".gitignore",
    }


def test_dot_git_is_a_file(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """
    Test that each_unignored_file() does not crash when .git is a file (e.g.,
    if the build is being run in a submodule)
    """
    monkeypatch.chdir(tmp_path)
    # Create a file named .git
    git = Path(".git")
    git.write_text("gitdir: ../../.git/modules/foo")
    # If this throws an exception, the test will fail
    assert list(each_unignored_file(Path())) == []
