from __future__ import annotations

from pathlib import Path

import pytest

from scikit_build_core.resources._editable_redirect import (
    FileLockIfUnix,
    ScikitBuildRedirectingFinder,
    install,
)


def process_dict(d: dict[str, str]) -> dict[str, str]:
    return {k: str(Path(v)) for k, v in d.items()}


def process_dict_set(d: dict[str, set[str]]) -> dict[str, set[str]]:
    return {k: {str(Path(x)) for x in v} for k, v in d.items()}


def test_editable_redirect():
    known_source_files = process_dict(
        {
            "pkg": "/source/pkg/__init__.py",
            "pkg.module": "/source/pkg/module.py",
            "pkg.subpkg": "/source/pkg/subpkg/__init__.py",
            "pkg.subpkg.module": "/source/pkg/subpkg/module.py",
            "pkg.resources.file": "/source/pkg/resources/file.txt",
            "pkg.namespace.module": "/source/pkg/namespace/module.py",
        }
    )
    known_wheel_files = process_dict(
        {
            "pkg.subpkg.source": "pkg/subpkg/source.py",
            "pkg.src_files": "pkg/src_files.py",
            "pkg.namespace.source": "pkg/namespace/source.py",
            "pkg.iresources.file": "pkg/iresources/file.txt",
            "pkg.installed_files": "pkg/installed_files.py",
            "pkg.source": "pkg/source.py",
        }
    )

    finder = ScikitBuildRedirectingFinder(
        known_source_files=known_source_files,
        known_wheel_files=known_wheel_files,
        path=None,
        rebuild=False,
        verbose=False,
        build_options=[],
        install_options=[],
        dir=str(Path("/sitepackages")),
        install_dir="",
    )

    assert finder.submodule_search_locations == process_dict_set(
        {
            "pkg": {
                "/sitepackages/pkg",
                "/source/pkg",
            },
            "pkg.iresources": {
                "/sitepackages/pkg/iresources",
            },
            "pkg.namespace": {
                "/sitepackages/pkg/namespace",
                "/source/pkg/namespace",
            },
            "pkg.resources": {"/source/pkg/resources"},
            "pkg.subpkg": {
                "/sitepackages/pkg/subpkg",
                "/source/pkg/subpkg",
            },
        }
    )
    assert finder.pkgs == ["pkg", "pkg.subpkg"]


def test_find_spec_source():
    finder = ScikitBuildRedirectingFinder(
        known_source_files={"mod": "/src/mod.py"},
        known_wheel_files={},
        path=None,
        rebuild=False,
        verbose=False,
        build_options=[],
        install_options=[],
        dir="/sp",
        install_dir="",
    )
    spec = finder.find_spec("mod")
    assert spec is not None
    assert spec.origin == "/src/mod.py"


def test_find_spec_wheel():
    finder = ScikitBuildRedirectingFinder(
        known_source_files={},
        known_wheel_files={"mod": "mod.py"},
        path=None,
        rebuild=False,
        verbose=False,
        build_options=[],
        install_options=[],
        dir="/sp",
        install_dir="",
    )
    spec = finder.find_spec("mod")
    assert spec is not None
    assert spec.origin == str(Path("/sp/mod.py"))


def test_find_spec_package():
    finder = ScikitBuildRedirectingFinder(
        known_source_files={"pkg": "/src/pkg/__init__.py"},
        known_wheel_files={},
        path=None,
        rebuild=False,
        verbose=False,
        build_options=[],
        install_options=[],
        dir="/sp",
        install_dir="",
    )
    spec = finder.find_spec("pkg")
    assert spec is not None
    assert spec.submodule_search_locations is not None


def test_find_spec_unknown():
    finder = ScikitBuildRedirectingFinder(
        known_source_files={},
        known_wheel_files={},
        path=None,
        rebuild=False,
        verbose=False,
        build_options=[],
        install_options=[],
        dir="/sp",
        install_dir="",
    )
    assert finder.find_spec("unknown") is None


def test_install_inserts_meta_path():
    import sys

    before = len(sys.meta_path)
    install(
        known_source_files={"mod": "/src/mod.py"},
        known_wheel_files={},
        path=None,
    )
    assert len(sys.meta_path) == before + 1
    # clean up
    sys.meta_path.pop(0)


def test_filelock_if_unix_no_fcntl(tmp_path):
    # Skip on Windows where fcntl isn't available
    pytest.importorskip("fcntl")

    lock = FileLockIfUnix(str(tmp_path / "editable_rebuild.lock"))
    lock.acquire()
    assert lock.lock_file_fd is not None
    lock.release()


def test_filelock_if_unix_missing_fcntl(monkeypatch, tmp_path):
    import builtins

    real_import = builtins.__import__
    fcntl_msg = "No module named 'fcntl'"

    def fake_import(name, *args, **kwargs):
        if name == "fcntl":
            raise ModuleNotFoundError(fcntl_msg)
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", fake_import)

    lock = FileLockIfUnix(str(tmp_path / "editable_rebuild.lock"))
    lock.acquire()
    assert lock.lock_file_fd is None
    lock.release()
    # Should not raise
