from __future__ import annotations

import os
import shutil
import subprocess
import tarfile
from pathlib import Path

import pytest

import scikit_build_core.build
from scikit_build_core._logging import rich_warning
from scikit_build_core.build import _file_processor, build_sdist
from scikit_build_core.build._file_processor import each_unignored_file
from scikit_build_core.errors import ScikitBuildError, UnsupportedOperation

pytestmark = pytest.mark.skipif(shutil.which("git") is None, reason="git required")


@pytest.fixture(autouse=True)
def git_env(monkeypatch: pytest.MonkeyPatch) -> None:
    for var in ("AUTHOR", "COMMITTER"):
        monkeypatch.setenv(f"GIT_{var}_NAME", "a")
        monkeypatch.setenv(f"GIT_{var}_EMAIL", "a@example.com")
    monkeypatch.setenv("GIT_CONFIG_GLOBAL", os.devnull)
    monkeypatch.setenv("GIT_CONFIG_NOSYSTEM", "1")
    _file_processor.clear_git_cache()
    rich_warning.cache_clear()


def git(*args: str, cwd: Path | str = ".") -> None:
    subprocess.run(
        ["git", "-c", "protocol.file.allow=always", *args],
        cwd=cwd,
        check=True,
        capture_output=True,
    )


def make_repo(path: Path, files: dict[str, str]) -> None:
    path.mkdir(parents=True, exist_ok=True)
    git("init", "-q", cwd=path)
    for name, contents in files.items():
        (path / name).parent.mkdir(parents=True, exist_ok=True)
        (path / name).write_text(contents, encoding="utf-8")
    git("add", "-f", *files, cwd=path)
    git("commit", "-qm", "init", cwd=path)


def files(*args: str) -> set[Path]:
    return {Path(a) for a in args}


@pytest.fixture
def repo(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """A repository with a tracked file matching its own .gitignore."""
    make_repo(
        tmp_path / "repo",
        {
            ".gitignore": "*.log\n",
            "pyproject.toml": "",
            "tracked.log": "",
            "src/pkg/__init__.py": "",
        },
    )
    monkeypatch.chdir(tmp_path / "repo")
    Path("untracked.py").write_text("", encoding="utf-8")
    Path("ignored.log").write_text("", encoding="utf-8")
    Path("src/pkg/untracked.py").write_text("", encoding="utf-8")
    return tmp_path / "repo"


@pytest.mark.usefixtures("repo")
def test_git_mode_tracked_only() -> None:
    assert set(each_unignored_file(Path(), mode="git")) == files(
        ".gitignore", "pyproject.toml", "tracked.log", "src/pkg/__init__.py"
    )


@pytest.mark.usefixtures("repo")
def test_git_mode_include_exclude(monkeypatch: pytest.MonkeyPatch) -> None:
    # Untracked files come from git, not from a walk of the project.
    monkeypatch.setattr(os, "walk", None)
    result = set(
        each_unignored_file(
            Path(),
            include=["untracked.py", "src/**/*.py"],
            exclude=["*.log", "src/"],
            mode="git",
        )
    )
    # Include adds untracked files and wins over exclude, as in "manual".
    assert result == files(
        ".gitignore",
        "pyproject.toml",
        "untracked.py",
        "src/pkg/__init__.py",
        "src/pkg/untracked.py",
    )


@pytest.mark.usefixtures("repo")
def test_git_mode_starting_path() -> None:
    assert set(each_unignored_file(Path("src/pkg"), mode="git")) == files(
        "src/pkg/__init__.py"
    )


@pytest.mark.usefixtures("repo")
def test_git_mode_build_dir_and_missing(capsys: pytest.CaptureFixture[str]) -> None:
    Path("tracked.log").unlink()
    Path("build").mkdir()
    Path("build/out.txt").write_text("", encoding="utf-8")
    git("add", "-f", "build/out.txt")
    assert set(each_unignored_file(Path(), build_dir="build", mode="git")) == files(
        ".gitignore", "pyproject.toml", "src/pkg/__init__.py"
    )
    assert "tracked.log" in capsys.readouterr().err


@pytest.mark.usefixtures("repo")
def test_git_mode_runs_git_once(monkeypatch: pytest.MonkeyPatch) -> None:
    calls = []
    run = subprocess.run

    def counting_run(*args: object, **kwargs: object) -> object:
        calls.append(args)
        return run(*args, **kwargs)  # type: ignore[call-overload]

    monkeypatch.setattr(subprocess, "run", counting_run)
    list(each_unignored_file(Path("src"), mode="git"))
    list(each_unignored_file(Path("src/pkg"), mode="git"))
    assert len(calls) == 1


@pytest.mark.usefixtures("repo")
def test_git_mode_broken_repo(capsys: pytest.CaptureFixture[str]) -> None:
    """A git error inside a checkout is not a reason to quietly walk."""
    Path(".git/index").write_bytes(b"garbage")
    with pytest.raises(UnsupportedOperation):
        list(each_unignored_file(Path(), mode="git"))
    assert set(each_unignored_file(Path(), mode="git", require_git=False)) == files(
        ".gitignore",
        "pyproject.toml",
        "tracked.log",
        "ignored.log",
        "untracked.py",
        "src/pkg/__init__.py",
        "src/pkg/untracked.py",
    )
    assert "WARNING" in capsys.readouterr().err


def test_git_mode_submodules(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    make_repo(tmp_path / "inner", {".gitignore": "*.cpp\n", "a.cpp": ""})
    make_repo(
        tmp_path / "sub",
        {".gitignore": "gen/\n*.cpp\n", "gen/g.c": "", "own.cpp": ""},
    )
    git("submodule", "add", "-q", "../inner", "inner", cwd=tmp_path / "sub")
    git("commit", "-qm", "sub", cwd=tmp_path / "sub")
    make_repo(tmp_path / "top", {".gitignore": "gen\n", "pyproject.toml": ""})
    monkeypatch.chdir(tmp_path / "top")
    git("submodule", "add", "-q", "../sub", "ext/sub")
    git("submodule", "update", "-q", "--init", "--recursive")
    git("commit", "-qm", "top")
    Path("ext/sub/inner/new.cpp").write_text("", encoding="utf-8")

    assert set(each_unignored_file(Path(), include=["*.cpp"], mode="git")) == files(
        ".gitignore",
        ".gitmodules",
        "pyproject.toml",
        "ext/sub/.gitignore",
        "ext/sub/.gitmodules",
        "ext/sub/gen/g.c",
        "ext/sub/own.cpp",
        "ext/sub/inner/.gitignore",
        "ext/sub/inner/a.cpp",
        "ext/sub/inner/new.cpp",
    )
    assert set(each_unignored_file(Path(), mode="git")) == files(
        ".gitignore",
        ".gitmodules",
        "pyproject.toml",
        "ext/sub/.gitignore",
        "ext/sub/.gitmodules",
        "ext/sub/gen/g.c",
        "ext/sub/own.cpp",
        "ext/sub/inner/.gitignore",
        "ext/sub/inner/a.cpp",
    )

    git("submodule", "deinit", "-q", "--all")
    _file_processor.clear_git_cache()
    with pytest.raises(ScikitBuildError, match="ext/sub"):
        list(each_unignored_file(Path(), mode="git"))
    # A package walk only needs the submodules below it.
    Path("pkg").mkdir()
    assert list(each_unignored_file(Path("pkg"), mode="git")) == []


@pytest.mark.usefixtures("repo")
def test_git_mode_dir_symlink() -> None:
    try:
        Path("link").symlink_to("src")
    except OSError:
        pytest.skip("symlinks not supported")
    git("add", "link")

    assert set(each_unignored_file(Path(), mode="git", resolve_symlinks="none")) == (
        files(".gitignore", "pyproject.toml", "tracked.log", "src/pkg/__init__.py")
        | files("link")
    )
    # A followed link inside the project carries only tracked files.
    assert set(each_unignored_file(Path(), mode="git", resolve_symlinks="all")) == (
        files(".gitignore", "pyproject.toml", "tracked.log", "src/pkg/__init__.py")
        | files("link/pkg/__init__.py")
    )
    assert set(each_unignored_file(Path("link/pkg"), mode="git")) == files(
        "link/pkg/__init__.py"
    )


def test_git_mode_external_symlink(repo: Path) -> None:
    (repo.parent / "outside").mkdir()
    (repo.parent / "outside/data.txt").write_text("", encoding="utf-8")
    try:
        Path("ext").symlink_to("../outside")
    except OSError:
        pytest.skip("symlinks not supported")
    git("add", "ext")

    # Git can't describe an external target, so it is walked.
    assert set(each_unignored_file(Path(), mode="git")) == files(
        ".gitignore",
        "pyproject.toml",
        "tracked.log",
        "src/pkg/__init__.py",
        "ext/data.txt",
    )
    assert set(each_unignored_file(Path("ext"), mode="git")) == files("ext/data.txt")


def test_git_mode_no_repo(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("GIT_CEILING_DIRECTORIES", str(tmp_path))
    monkeypatch.chdir(tmp_path)
    Path("pyproject.toml").write_text("", encoding="utf-8")
    Path(".gitignore").write_text("*.py\n", encoding="utf-8")
    Path("a.py").write_text("", encoding="utf-8")

    with pytest.raises(UnsupportedOperation):
        list(each_unignored_file(Path(), mode="git"))
    assert set(each_unignored_file(Path(), mode="git", require_git=False)) == files(
        "pyproject.toml", ".gitignore", "a.py"
    )


def test_git_mode_untracked_project(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """An unpacked SDist inside an unrelated checkout is not a git project."""
    make_repo(tmp_path, {"other": ""})
    (tmp_path / "proj").mkdir()
    monkeypatch.chdir(tmp_path / "proj")
    Path("pyproject.toml").write_text("", encoding="utf-8")

    with pytest.raises(UnsupportedOperation, match=r"pyproject\.toml"):
        list(each_unignored_file(Path(), mode="git"))
    assert set(each_unignored_file(Path(), mode="git", require_git=False)) == files(
        "pyproject.toml"
    )


def test_unsupported_operation_on_backend() -> None:
    assert scikit_build_core.build.UnsupportedOperation is UnsupportedOperation


@pytest.mark.usefixtures("package_simple_pyproject_ext")
def test_pep517_sdist_git_mode(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("GIT_CEILING_DIRECTORIES", str(Path.cwd().parent))
    config: dict[str, list[str] | str] = {"sdist.inclusion-mode": "git"}
    sdist_dir = tmp_path / "dist"

    with pytest.raises(UnsupportedOperation):
        build_sdist(str(sdist_dir), config)

    make_repo(Path(), {"pyproject.toml": Path("pyproject.toml").read_text()})
    git("add", "CMakeLists.txt")
    Path("untracked.txt").write_text("", encoding="utf-8")

    out = build_sdist(str(sdist_dir), config)
    with tarfile.open(sdist_dir / out) as tar:
        names = {Path(n).relative_to("cmake_example-0.0.1") for n in tar.getnames()}
    assert names == files("pyproject.toml", "CMakeLists.txt", "PKG-INFO")
