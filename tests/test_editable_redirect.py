from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

from scikit_build_core.resources._editable_redirect import (
    ScikitBuildRedirectingFinder,
    install,
)


def process_dict_set(d: dict[str, set[str]]) -> dict[str, set[str]]:
    return {k: {str(Path(x)) for x in v} for k, v in d.items()}


def test_editable_redirect():
    # known_directories drives __path__: install-tree dirs are relative (joined
    # with `dir` at runtime), source-tree dirs are absolute. Data-only dirs
    # (pkg.resources, pkg.iresources) are present here without any module entry.
    known_directories = process_dict_set(
        {
            "pkg": {"pkg", "/source/pkg"},
            "pkg.iresources": {"pkg/iresources"},
            "pkg.namespace": {"pkg/namespace", "/source/pkg/namespace"},
            "pkg.resources": {"/source/pkg/resources"},
            "pkg.subpkg": {"pkg/subpkg", "/source/pkg/subpkg"},
        }
    )
    finder = ScikitBuildRedirectingFinder(
        known_source_files={},
        known_wheel_files={},
        known_directories={k: sorted(v) for k, v in known_directories.items()},
        known_packages=["pkg", "pkg.subpkg"],
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
        known_directories={},
        known_packages=[],
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


def test_rebuild_runs_once_per_process(tmp_path: Path):
    """Regression (#1367): rebuild fires at most once per finder, not per import.

    Importing a project like pytorch resolves many compiled modules at
    ``import torch``; each known wheel file should not re-trigger an (otherwise
    no-op) ``cmake --build``/``--install`` cycle.
    """
    finder = ScikitBuildRedirectingFinder(
        known_source_files={},
        known_wheel_files={
            "pkg._mod_a": "pkg/_mod_a.so",
            "pkg._mod_b": "pkg/_mod_b.so",
        },
        known_directories={},
        known_packages=[],
        path=str(tmp_path),
        rebuild=True,
        verbose=False,
        build_options=[],
        install_options=[],
        dir=str(tmp_path),
        install_dir="",
    )

    calls = 0

    def fake_rebuild() -> None:
        nonlocal calls
        calls += 1

    finder.rebuild = fake_rebuild  # type: ignore[method-assign]

    finder.find_spec("pkg._mod_a")
    finder.find_spec("pkg._mod_a")
    finder.find_spec("pkg._mod_b")

    assert calls == 1


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


def test_libdir_to_installed_absolute(tmp_path: Path):
    """With absolute=True the install-tree files are recorded as absolute paths.

    Used by rebuildable editables that point at a persistent build-dir install
    tree (#1135): the redirect references the compiled artifacts there directly,
    so they need no copy in site-packages and no reconfigure on rebuild.
    """
    import importlib.machinery

    from scikit_build_core.build._editable import libdir_to_installed

    ext = importlib.machinery.EXTENSION_SUFFIXES[0]
    libdir = tmp_path / "install" / "platlib"
    mod = libdir / "pkg" / f"_module{ext}"
    mod.parent.mkdir(parents=True)
    mod.touch()

    relative = libdir_to_installed(libdir)
    assert relative == {"pkg._module": str(Path(f"pkg/_module{ext}"))}

    absolute = libdir_to_installed(libdir, absolute=True)
    assert absolute == {"pkg._module": str(mod)}
    assert Path(absolute["pkg._module"]).is_absolute()


def test_collect_search_locations_absolute(tmp_path: Path):
    """With absolute=True the install-tree __path__ entries are absolute."""
    import importlib.machinery

    from scikit_build_core.build._editable import collect_search_locations

    ext = importlib.machinery.EXTENSION_SUFFIXES[0]
    libdir = tmp_path / "install" / "platlib"
    mod = libdir / "pkg" / f"_module{ext}"
    mod.parent.mkdir(parents=True)
    mod.touch()

    directories, packages = collect_search_locations({}, libdir, absolute=True)
    assert packages == []
    assert directories == {"pkg": [str(libdir / "pkg")]}


def test_editable_redirect_external_install_tree(tmp_path: Path):
    """An external (absolute) install tree resolves and rebuilds in place (#1135).

    A rebuildable editable bakes the persistent install prefix at build time, so
    the redirect resolves compiled modules to absolute build-tree paths and the
    rebuild's ``cmake --install --prefix`` points there -- no reconfigure needed.
    """
    import importlib.machinery

    ext = importlib.machinery.EXTENSION_SUFFIXES[0]
    install_prefix = tmp_path / "build" / "install" / "platlib"
    mod = install_prefix / "pkg" / f"_module{ext}"
    mod.parent.mkdir(parents=True)
    mod.touch()

    finder = ScikitBuildRedirectingFinder(
        known_source_files={},
        known_wheel_files={"pkg._module": str(mod)},
        known_directories={"pkg": [str(install_prefix / "pkg")]},
        known_packages=[],
        path=str(tmp_path / "build"),
        rebuild=False,
        verbose=False,
        build_options=[],
        install_options=[],
        dir=str(tmp_path / "site-packages"),
        install_dir=str(install_prefix),
    )

    # An absolute known_wheel_file is used verbatim, not joined under site-packages.
    spec = finder.find_spec("pkg._module")
    assert spec is not None
    assert spec.origin == str(mod)

    # The rebuild --prefix is the absolute install tree, so the cached
    # SKBUILD_<targetlib>_DIR / CMAKE_INSTALL_PREFIX stay valid without a redo.
    assert finder.install_dir == str(install_prefix)


def test_mapping_to_modules_keeps_symlink_in_package_dir(tmp_path: Path):
    """A symlinked-in module keeps its in-package directory, not the link target (#647)."""
    from scikit_build_core.build._editable import mapping_to_modules

    # A monorepo layout: shared/shared_mod.py is symlinked into src/pkg/.
    shared = tmp_path / "shared"
    shared.mkdir()
    (shared / "shared_mod.py").write_text("value = 1\n")
    # An unrelated sibling file that must NOT become importable as pkg.unrelated.
    (shared / "unrelated.py").write_text("value = 2\n")

    pkg_src = tmp_path / "src" / "pkg"
    pkg_src.mkdir(parents=True)
    (pkg_src / "__init__.py").touch()
    symlink = pkg_src / "shared_mod.py"
    symlink.symlink_to(shared / "shared_mod.py")

    libdir = tmp_path / "site-packages"
    mapping = {
        str(pkg_src / "__init__.py"): str(libdir / "pkg/__init__.py"),
        str(symlink): str(libdir / "pkg/shared_mod.py"),
    }
    result = mapping_to_modules(mapping, libdir)

    # The recorded source path must stay inside the package (the symlink path),
    # not point at the resolved target dir (shared/), which would otherwise leak
    # into pkg.__path__ and make shared/unrelated.py importable as pkg.unrelated.
    assert Path(result["pkg.shared_mod"]).parent == pkg_src
    assert Path(result["pkg.shared_mod"]).parent != shared.resolve()
