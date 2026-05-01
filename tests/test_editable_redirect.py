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
    """Test that .pxd/__init__.pxd files are recognized as packages."""
    known_source_files = process_dict(
        {
            "pkg.cython_subpkg": "/source/pkg/cython_subpkg/__init__.pxd",
            "pkg.pyx_subpkg": "/source/pkg/pyx_subpkg/__init__.pyx",
        }
    )
    known_wheel_files = process_dict({})

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

    # Bug 1: .pxd/.pyx files are not recognized as packages
    assert "pkg.cython_subpkg" in finder.pkgs
    assert "pkg.pyx_subpkg" in finder.pkgs

    # Bug 1: .pxd/.pyx packages should have their own search locations
    assert "pkg.cython_subpkg" in finder.submodule_search_locations
    assert "pkg.pyx_subpkg" in finder.submodule_search_locations

    # Bug 2: find_spec should recognize .pxd/.pyx as packages
    spec_pxd = finder.find_spec("pkg.cython_subpkg")
    assert spec_pxd is not None
    assert spec_pxd.submodule_search_locations is not None

    spec_pyx = finder.find_spec("pkg.pyx_subpkg")
    assert spec_pyx is not None
    assert spec_pyx.submodule_search_locations is not None


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
