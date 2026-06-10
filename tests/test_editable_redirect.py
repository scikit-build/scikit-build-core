from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

from scikit_build_core.resources._editable_redirect import (
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
    assert finder.pkgs == frozenset(["pkg", "pkg.subpkg"])


def test_editable_redirect_pxd():
    """Test that .pxd/.pyx __init__ files are recognized as packages.

    If packages have both __init__.py and __init__.pxd, the file scanner may pick up the
    .pxd as the representative file for the package init and produce the wrong __path__.
    """
    known_source_files = process_dict(
        {
            "pkg": "/source/pkg/__init__.py",
            "pkg.module": "/source/pkg/module.py",
            # Cython subpackage whose init was picked up as .pxd (not .py)
            "pkg.cython_subpkg": "/source/pkg/cython_subpkg/__init__.pxd",
            "pkg.cython_subpkg.impl": "/source/pkg/cython_subpkg/impl.pyx",
            # Pyx subpackage
            "pkg.pyx_subpkg": "/source/pkg/pyx_subpkg/__init__.pyx",
            "pkg.pyx_subpkg.module": "/source/pkg/pyx_subpkg/module.py",
        }
    )
    known_wheel_files = process_dict(
        {"pkg.cython_subpkg.compiled": "pkg/cython_subpkg/compiled.abi3.so"}
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

    # .pxd/.pyx init files should be recognized as packages
    assert "pkg.cython_subpkg" in finder.pkgs
    assert "pkg.pyx_subpkg" in finder.pkgs

    # Cython subpackages must have their OWN search locations
    assert "pkg.cython_subpkg" in finder.submodule_search_locations
    assert "pkg.pyx_subpkg" in finder.submodule_search_locations

    # parent pkg.__path__ must NOT be polluted with child package dirs
    pkg_paths = finder.submodule_search_locations.get("pkg", set())
    assert not any("cython_subpkg" in p for p in pkg_paths), (
        f"pkg.__path__ is polluted with cython_subpkg: {pkg_paths}"
    )
    assert not any("pyx_subpkg" in p for p in pkg_paths), (
        f"pkg.__path__ is polluted with pyx_subpkg: {pkg_paths}"
    )


@pytest.fixture
def _restore_meta_path():
    saved = sys.meta_path[:]
    try:
        yield
    finally:
        sys.meta_path[:] = saved


@pytest.mark.usefixtures("_restore_meta_path")
def test_install_is_idempotent():
    """PEP 829 .start entry points may be invoked more than once.

    CPython 3.15 processes a venv's site-packages twice during startup, so the
    .start entry point runs twice. ``install`` must not insert a second finder.
    """

    def count_finders() -> int:
        return sum(isinstance(f, ScikitBuildRedirectingFinder) for f in sys.meta_path)

    assert count_finders() == 0
    install({}, {}, None)
    assert count_finders() == 1
    install({}, {}, None)
    assert count_finders() == 1


@pytest.mark.usefixtures("_restore_meta_path")
def test_install_multiple_packages():
    """Several scikit-build-core editable packages can share an environment.

    Each package emits its own ``.start`` whose ``entrypoint()`` calls
    ``install`` with that package's own module maps. The idempotency guard must
    be keyed to the package, so a second (different) package still registers its
    finder, while re-running the same package's entry point does not.
    """

    def count_finders() -> int:
        return sum(isinstance(f, ScikitBuildRedirectingFinder) for f in sys.meta_path)

    pkg_a: tuple[dict[str, str], dict[str, str]] = (
        {"pkg_a": "/src/pkg_a/__init__.py"},
        {},
    )
    pkg_b: tuple[dict[str, str], dict[str, str]] = (
        {"pkg_b": "/src/pkg_b/__init__.py"},
        {},
    )

    assert count_finders() == 0
    install(*pkg_a, None)
    assert count_finders() == 1
    install(*pkg_b, None)
    assert count_finders() == 2
    # Re-running either package's entry point must not add a duplicate.
    install(*pkg_a, None)
    install(*pkg_b, None)
    assert count_finders() == 2


def _make_finder(tmp_path: Path, *, verbose: bool) -> ScikitBuildRedirectingFinder:
    return ScikitBuildRedirectingFinder(
        known_source_files={},
        known_wheel_files={},
        path=str(tmp_path),
        rebuild=True,
        verbose=verbose,
        build_options=[],
        install_options=[],
        dir=str(tmp_path),
        install_dir="",
    )


def test_rebuild_failure_surfaces_stdout_when_not_verbose(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
):
    """Regression: a failed non-verbose build captured stdout but never printed it.

    The error branch used ``and verbose`` (verbose already streams live), so the
    captured stdout from the failing build (e.g. MSBuild writes to stdout) was
    silently dropped. It should print when *not* verbose.
    """

    def fake_run(
        command: list[str], **kwargs: object
    ) -> subprocess.CompletedProcess[str]:
        assert kwargs["stdout"] == subprocess.PIPE
        return subprocess.CompletedProcess(
            command, returncode=1, stdout="boom build error", stderr=""
        )

    monkeypatch.setattr(
        "scikit_build_core.resources._editable_redirect.subprocess.run", fake_run
    )

    finder = _make_finder(tmp_path, verbose=False)
    with pytest.raises(subprocess.CalledProcessError):
        finder.rebuild()

    captured = capsys.readouterr()
    assert "boom build error" in captured.err
    # Must not print the literal "None" (the old verbose branch did this).
    assert "ERROR: None" not in captured.err


def test_rebuild_success_runs_build_and_install(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    calls: list[list[str]] = []

    def fake_run(
        command: list[str],
        **kwargs: object,  # noqa: ARG001
    ) -> subprocess.CompletedProcess[str]:
        calls.append(list(command))
        return subprocess.CompletedProcess(command, returncode=0, stdout="", stderr="")

    monkeypatch.setattr(
        "scikit_build_core.resources._editable_redirect.subprocess.run", fake_run
    )

    finder = _make_finder(tmp_path, verbose=False)
    finder.rebuild()

    assert calls[0][:2] == ["cmake", "--build"]
    assert calls[1][:2] == ["cmake", "--install"]


def test_mapping_to_modules_prefers_py():
    """Test that mapping_to_modules prefers __init__.py over __init__.pxd."""
    from scikit_build_core.build._editable import mapping_to_modules

    libdir = Path("/site-packages")
    mapping = {
        "/source/pkg/__init__.py": "/site-packages/pkg/__init__.py",
        "/source/pkg/__init__.pxd": "/site-packages/pkg/__init__.pxd",
        "/source/pkg/module.py": "/site-packages/pkg/module.py",
    }
    result = mapping_to_modules(mapping, libdir)

    # Bug 3: .py should win over .pxd (currently .pxd overwrites .py)
    assert result["pkg"].endswith("__init__.py")
