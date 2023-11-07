from __future__ import annotations

import textwrap
import typing
from pathlib import Path
from typing import NamedTuple

import pytest

from scikit_build_core.build._editable import (
    editable_redirect,
    libdir_to_installed,
    mapping_to_modules,
)
from scikit_build_core.build._pathutil import packages_to_file_mapping

if typing.TYPE_CHECKING:
    from conftest import VEnv


class EditablePackage(NamedTuple):
    site_packages: Path
    pkg_dir: Path
    src_pkg_dir: Path


@pytest.fixture(
    params=[
        pytest.param(False, id="abs"),
        pytest.param(True, id="rel"),
    ]
)
def editable_package(
    request: pytest.FixtureRequest,
    tmp_path: Path,
    virtualenv: VEnv,
    monkeypatch: pytest.MonkeyPatch,
):
    rel = request.param

    prefix = "" if rel else "pkg"

    source_dir = tmp_path / "source"
    source_dir.mkdir()
    # Functions in build.wheel require running from this dir
    monkeypatch.chdir(source_dir)

    site_packages = virtualenv.purelib

    # Create a fake package
    pkg_dir = site_packages / "pkg"
    pkg_dir.mkdir()
    src_pkg_dir = source_dir / "pkg"
    src_pkg_dir.mkdir()

    # Make some fake files
    (src_pkg_dir / "__init__.py").touch()
    (src_pkg_dir / "module.py").write_text(
        textwrap.dedent(
            f"""\
            from {prefix}.subpkg import module
            from {prefix}.subpkg import source
            from {prefix}.namespace import module
            from {prefix}.namespace import source
            """
        )
    )
    (pkg_dir / "source.py").write_text(
        textwrap.dedent(
            f"""\
            from {prefix}.subpkg import module
            from {prefix}.subpkg import source
            from {prefix}.namespace import module
            from {prefix}.namespace import source
            """
        )
    )

    src_sub_package = src_pkg_dir / "subpkg"
    src_sub_package.mkdir()
    src_sub_package.joinpath("__init__.py").touch()
    src_sub_package.joinpath("module.py").touch()

    sub_package = pkg_dir / "subpkg"
    sub_package.mkdir()
    sub_package.joinpath("source.py").touch()

    src_namespace_pkg = src_pkg_dir / "namespace"
    src_namespace_pkg.mkdir()
    src_namespace_pkg.joinpath("module.py").touch()

    namespace_pkg = pkg_dir / "namespace"
    namespace_pkg.mkdir()
    namespace_pkg.joinpath("source.py").touch()

    return EditablePackage(site_packages, pkg_dir, src_pkg_dir)


def test_navigate_editable_pkg(editable_package: EditablePackage, virtualenv: VEnv):
    site_packages, pkg_dir, src_pkg_dir = editable_package

    # Create a fake editable install
    packages = ["pkg"]
    mapping = packages_to_file_mapping(
        packages=packages,
        platlib_dir=site_packages,
        include=[],
        exclude=[],
    )
    assert mapping == {
        str(Path("pkg/__init__.py")): str(pkg_dir / "__init__.py"),
        str(Path("pkg/module.py")): str(pkg_dir / "module.py"),
        str(Path("pkg/namespace/module.py")): str(pkg_dir / "namespace/module.py"),
        str(Path("pkg/subpkg/__init__.py")): str(pkg_dir / "subpkg/__init__.py"),
        str(Path("pkg/subpkg/module.py")): str(pkg_dir / "subpkg/module.py"),
    }
    modules = mapping_to_modules(mapping, libdir=site_packages)

    assert modules == {
        "pkg": str(src_pkg_dir / "__init__.py"),
        "pkg.module": str(src_pkg_dir / "module.py"),
        "pkg.namespace.module": str(src_pkg_dir / "namespace/module.py"),
        "pkg.subpkg": str(src_pkg_dir / "subpkg/__init__.py"),
        "pkg.subpkg.module": str(src_pkg_dir / "subpkg/module.py"),
    }

    installed = libdir_to_installed(site_packages)
    installed = {k: v for k, v in installed.items() if k.startswith("pkg")}

    assert installed == {
        "pkg.subpkg.source": str(Path("pkg/subpkg/source.py")),
        "pkg.namespace.source": str(Path("pkg/namespace/source.py")),
        "pkg.source": str(Path("pkg/source.py")),
    }

    editable_txt = editable_redirect(
        modules=modules,
        installed=installed,
        reload_dir=None,
        rebuild=False,
        verbose=False,
        build_options=[],
        install_options=[],
    )

    site_packages.joinpath("_pkg_editable.py").write_text(editable_txt)
    site_packages.joinpath("_pkg_editable.pth").write_text("import _pkg_editable\n")

    # Test the editable install
    virtualenv.execute("import pkg.subpkg")
    virtualenv.execute("import pkg.subpkg.module")
    virtualenv.execute("import pkg.subpkg.source")
    virtualenv.execute("import pkg.namespace.module")
    virtualenv.execute("import pkg.namespace.source")
    # This allows debug print statements in _editable_redirect.py to be seen
    print(virtualenv.execute("import pkg.module"))
    print(virtualenv.execute("import pkg.source"))
