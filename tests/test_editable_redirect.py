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
