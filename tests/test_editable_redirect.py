from __future__ import annotations

from pathlib import Path

from scikit_build_core.resources._editable_redirect import ScikitBuildRedirectingFinder


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


def test_editable_redirect_pxd():
    """Test that .pxd/.pyx __init__ files are recognized as packages.

    This mirrors real-world Cython projects (e.g. cuVS) where packages have
    both __init__.py and __init__.pxd, and where the file scanner may pick up
    the .pxd as the representative file for the package init.
    The key fix: the parent package's __path__ must NOT be polluted with the
    child package's directory.
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
    known_wheel_files = process_dict({"pkg.cython_subpkg.compiled": "pkg/cython_subpkg/compiled.abi3.so"})

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

    # Fix A: .pxd/.pyx init files should be recognized as packages
    assert "pkg.cython_subpkg" in finder.pkgs
    assert "pkg.pyx_subpkg" in finder.pkgs

    # Fix A: Cython subpackages must have their OWN search locations
    assert "pkg.cython_subpkg" in finder.submodule_search_locations
    assert "pkg.pyx_subpkg" in finder.submodule_search_locations

    # Critical: parent pkg.__path__ must NOT be polluted with child package dirs
    pkg_paths = finder.submodule_search_locations.get("pkg", set())
    assert not any("cython_subpkg" in p for p in pkg_paths), (
        f"pkg.__path__ is polluted with cython_subpkg: {pkg_paths}"
    )
    assert not any("pyx_subpkg" in p for p in pkg_paths), (
        f"pkg.__path__ is polluted with pyx_subpkg: {pkg_paths}"
    )

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
