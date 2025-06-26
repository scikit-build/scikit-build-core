from __future__ import annotations

import sys
from pathlib import Path
from typing import TYPE_CHECKING

import pytest

from scikit_build_core.build._file_processor import each_unignored_file

if TYPE_CHECKING:
    from collections.abc import Generator


def _mk_files(tmp_path: Path, files: str) -> Generator[Path, None, None]:
    """
    Create a set of files in the given temporary path based on the provided string.
    The string should contain file names
    """
    for line in files.splitlines():
        file_contents = line.strip()
        if file_contents:
            file_name, _, contents = file_contents.partition(":")
            file_path = tmp_path / file_name.strip()
            # Create parent directories if needed
            if not file_path.parent.is_dir():
                file_path.parent.mkdir(parents=True, exist_ok=True)
            file_path.write_text(contents.strip() or "content")
            yield file_path.relative_to(tmp_path)


def _setup_test_filesystem(tmp_path: Path) -> set[Path]:
    """
    Set up a test filesystem with various files and directories for testing.
    """

    return set(
        _mk_files(
            tmp_path,
            """
        README.md
        setup.py
        pyproject.toml
        src/__init__.py
        src/main.py
        src/utils.py
        tests/test_main.py
        tests/test_utils.py
        tests/tmp.py
        docs/index.md
        docs/api.rst
        temp.tmp: temporary file
        debug.log: log file
        cache.db: cache file
        local_ignored_file.txt
        __pycache__/test.pyc
        .git/config
        .gitignore: *tmp*
        .git/info/exclude: local_ignored_file.txt
        nested_dir/not_ignored.txt: not ignored file
    """,
        )
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


def test_include_patterns(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """
    Test that include patterns work correctly and override excludes.
    """
    monkeypatch.chdir(tmp_path)
    _setup_test_filesystem(tmp_path)

    # Test including only Python files
    result = set(each_unignored_file(Path(), include=["*.py"]))
    expected = {
        Path(s)
        for s in [
            ".gitignore",
            "README.md",
            "cache.db",
            "debug.log",
            "docs/api.rst",
            "docs/index.md",
            "nested_dir/not_ignored.txt",
            "pyproject.toml",
            "setup.py",
            "src/__init__.py",
            "src/main.py",
            "src/utils.py",
            "tests/test_main.py",
            "tests/test_utils.py",
            "tests/tmp.py",
        ]
    }
    assert result == expected

    # Test including specific files
    result = set(each_unignored_file(Path(), include=["tests/tmp.py"]))
    assert result == expected | {Path("tests/tmp.py")}

    # Test including with wildcards
    result = set(each_unignored_file(Path(), include=["tests/*"]))
    expected = expected | {Path("tests/tmp.py")}
    assert result == expected


def test_exclude_patterns(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """
    Test that exclude patterns work correctly.
    """
    monkeypatch.chdir(tmp_path)
    _setup_test_filesystem(tmp_path)

    # Test excluding specific file types
    result = set(each_unignored_file(Path(), exclude=["*.tmp", "*.log"]))
    expected = {
        Path(s)
        for s in [
            ".gitignore",
            "README.md",
            "cache.db",
            "docs/api.rst",
            "docs/index.md",
            "nested_dir/not_ignored.txt",
            "pyproject.toml",
            "setup.py",
            "src/__init__.py",
            "src/main.py",
            "src/utils.py",
            "tests/test_main.py",
            "tests/test_utils.py",
        ]
    }
    assert result == expected

    # Test excluding directories
    result = set(each_unignored_file(Path(), exclude=["tests/"]))
    expected = {
        Path(s)
        for s in [
            ".gitignore",
            "README.md",
            "cache.db",
            "debug.log",
            "docs/api.rst",
            "docs/index.md",
            "nested_dir/not_ignored.txt",
            "pyproject.toml",
            "setup.py",
            "src/__init__.py",
            "src/main.py",
            "src/utils.py",
        ]
    }
    assert result == expected

    # Test excluding with wildcards
    result = set(each_unignored_file(Path(), exclude=["*.py"]))
    expected = {
        Path(s)
        for s in [
            ".gitignore",
            "README.md",
            "cache.db",
            "debug.log",
            "docs/api.rst",
            "docs/index.md",
            "nested_dir/not_ignored.txt",
            "pyproject.toml",
        ]
    }
    assert result == expected


def test_include_overrides_exclude(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """
    Test that include patterns override exclude patterns.
    """
    monkeypatch.chdir(tmp_path)
    _setup_test_filesystem(tmp_path)

    # Exclude all files but include specific ones
    result = set(
        each_unignored_file(
            Path(), include=["src/main.py", "tests/test_main.py"], exclude=["*"]
        )
    )
    expected = {Path(s) for s in ["src/main.py", "tests/test_main.py"]}
    assert result == expected

    # Exclude everything but include a file from inside a directory
    result = set(
        each_unignored_file(Path(), include=["tests/test_main.py"], exclude=["*"])
    )
    expected = {Path(s) for s in ["tests/test_main.py"]}
    assert result == expected


def test_gitignore_interaction(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """
    Test interaction between include/exclude and gitignore files.
    """
    monkeypatch.chdir(tmp_path)
    _setup_test_filesystem(tmp_path)

    # Create .gitignore that excludes some files
    gitignore = tmp_path / ".gitignore"
    gitignore.write_text("*.tmp\n*.log\n/cache.db\n")

    # Test that gitignore is respected by default
    result = set(each_unignored_file(Path()))
    expected = {
        Path(s)
        for s in [
            ".gitignore",
            "README.md",
            "pyproject.toml",
            "setup.py",
            "src/__init__.py",
            "src/main.py",
            "src/utils.py",
            "tests/test_main.py",
            "tests/test_utils.py",
            "tests/tmp.py",
            "docs/index.md",
            "docs/api.rst",
            "nested_dir/not_ignored.txt",
        ]
    }
    assert result == expected

    # Test that include can override gitignore
    result = set(each_unignored_file(Path(), include=["*.tmp"]))
    assert result == expected | {Path("temp.tmp")}


def test_nested_gitignore(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """
    Test handling of nested .gitignore files.
    """
    monkeypatch.chdir(tmp_path)
    _setup_test_filesystem(tmp_path)

    # Create nested .gitignore in src directory
    src_gitignore = tmp_path / "src" / ".gitignore"
    src_gitignore.write_text("utils.py\n")

    # Test that nested gitignore is respected
    result = set(each_unignored_file(Path()))
    expected = {
        Path(s)
        for s in [
            ".gitignore",
            "README.md",
            "cache.db",
            "debug.log",
            "docs/api.rst",
            "docs/index.md",
            "nested_dir/not_ignored.txt",
            "pyproject.toml",
            "setup.py",
            "src/.gitignore",
            "src/__init__.py",
            "src/main.py",
            "tests/test_main.py",
            "tests/test_utils.py",
        ]
    }
    assert result == expected

    # Test that include can override nested gitignore
    result = set(each_unignored_file(Path(), include=["src/utils.py"]))
    assert result == expected | {Path("src/utils.py")}


def test_build_dir_exclusion(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """
    Test that build_dir parameter correctly excludes build directories.
    """
    monkeypatch.chdir(tmp_path)
    _setup_test_filesystem(tmp_path)

    # Create build directory
    build_dir = tmp_path / "build"
    build_dir.mkdir()
    build_file = build_dir / "output.so"
    build_file.write_text("compiled output")

    # Test that build directory is excluded when specified
    result = set(each_unignored_file(Path(), build_dir="build"))
    expected = {
        Path(s)
        for s in [
            ".gitignore",
            "README.md",
            "cache.db",
            "debug.log",
            "docs/api.rst",
            "docs/index.md",
            "nested_dir/not_ignored.txt",
            "pyproject.toml",
            "setup.py",
            "src/__init__.py",
            "src/main.py",
            "src/utils.py",
            "tests/test_main.py",
            "tests/test_utils.py",
        ]
    }
    assert result == expected
    assert build_file.relative_to(tmp_path) not in result

    # Test that include can override build_dir exclusion
    result = set(each_unignored_file(Path(), include=["build/*"], build_dir="build"))
    assert result == expected | {Path("build/output.so")}


def test_complex_combinations(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """
    Test complex combinations of include, exclude, gitignore, and build_dir.
    """
    monkeypatch.chdir(tmp_path)
    _setup_test_filesystem(tmp_path)

    # Set up complex scenario
    gitignore = tmp_path / ".gitignore"
    gitignore.write_text("*.tmp\ndebug.log\n")

    build_dir = tmp_path / "_build"
    build_dir.mkdir()
    build_file = build_dir / "lib.so"
    build_file.write_text("build output")

    # Complex pattern: exclude tests, include specific test, respect gitignore, exclude build
    result = set(
        each_unignored_file(
            Path(),
            include=[
                "tests/test_main.py",
                "*.tmp",
            ],  # Include specific test and override gitignore for .tmp
            exclude=["*"],  # Exclude tests dir and rst files
            build_dir="_build",
        )
    )

    expected = {
        Path(s) for s in ["tests/test_main.py", "temp.tmp"]
    }  # Only these should match
    assert result == expected


def test_empty_directory(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """
    Test behavior with empty directory.
    """
    monkeypatch.chdir(tmp_path)

    result = list(each_unignored_file(Path()))
    assert result == []

    result = list(each_unignored_file(Path(), include=["*.py"]))
    assert result == []

    result = list(each_unignored_file(Path(), exclude=["*.py"]))
    assert result == []


def test_nonexistent_patterns(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """
    Test behavior with patterns that don't match any files.
    """
    monkeypatch.chdir(tmp_path)
    _setup_test_filesystem(tmp_path)

    # Include pattern that matches nothing
    include_result = list(
        each_unignored_file(Path(), exclude=["*"], include=["*.nonexistent"])
    )
    assert include_result == []

    # Exclude pattern that matches nothing
    exclude_result = set(each_unignored_file(Path(), exclude=["*.nonexistent"]))
    expected = {
        Path(s)
        for s in [
            ".gitignore",
            "README.md",
            "cache.db",
            "debug.log",
            "docs/api.rst",
            "docs/index.md",
            "nested_dir/not_ignored.txt",
            "pyproject.toml",
            "setup.py",
            "src/__init__.py",
            "src/main.py",
            "src/utils.py",
            "tests/test_main.py",
            "tests/test_utils.py",
        ]
    }
    assert exclude_result == expected
