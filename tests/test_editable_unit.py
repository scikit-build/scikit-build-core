from __future__ import annotations

import sys
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
    src_pkg_dir.joinpath("__init__.py").touch()
    src_pkg_dir.joinpath("module.py").write_text(
        textwrap.dedent(
            f"""\
            from {prefix}.subpkg import module
            from {prefix}.subpkg import source
            from {prefix}.namespace import module
            from {prefix}.namespace import source
            """
        )
    )
    pkg_dir.joinpath("source.py").write_text(
        textwrap.dedent(
            f"""\
            from {prefix}.subpkg import module
            from {prefix}.subpkg import source
            from {prefix}.namespace import module
            from {prefix}.namespace import source
            """
        )
    )

    pkg_dir.joinpath("src_files.py").write_text(
        textwrap.dedent(
            """\
            import sys

            from importlib.resources import files

            read_file = files("pkg.resources").joinpath("file.txt").read_text(encoding="utf-8")
            assert read_file == "hello"
            """
        )
    )
    resources_dir = src_pkg_dir / "resources"
    resources_dir.mkdir()
    resources_dir.joinpath("file.txt").write_text("hello")

    pkg_dir.joinpath("installed_files.py").write_text(
        textwrap.dedent(
            """\
            from importlib.resources import files

            read_file = files("pkg.iresources").joinpath("file.txt").read_text(encoding="utf-8")
            assert read_file == "hi"
            """
        )
    )
    iresources_dir = pkg_dir / "iresources"
    iresources_dir.mkdir()
    iresources_dir.joinpath("file.txt").write_text("hi")

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


@pytest.mark.xfail(
    sys.version_info[:2] == (3, 9), reason="Python 3.9 not supported yet"
)
def test_navigate_editable_pkg(editable_package: EditablePackage, virtualenv: VEnv):
    site_packages, pkg_dir, src_pkg_dir = editable_package

    # Create a fake editable install
    packages = {"pkg": "pkg"}
    mapping = packages_to_file_mapping(
        packages=packages,
        platlib_dir=site_packages,
        include=[],
        src_exclude=[],
        target_exclude=[],
        build_dir="",
    )
    assert mapping == {
        str(Path("pkg/__init__.py")): str(pkg_dir / "__init__.py"),
        str(Path("pkg/module.py")): str(pkg_dir / "module.py"),
        str(Path("pkg/namespace/module.py")): str(pkg_dir / "namespace/module.py"),
        str(Path("pkg/subpkg/__init__.py")): str(pkg_dir / "subpkg/__init__.py"),
        str(Path("pkg/subpkg/module.py")): str(pkg_dir / "subpkg/module.py"),
        str(Path("pkg/resources/file.txt")): str(pkg_dir / "resources/file.txt"),
    }
    modules = mapping_to_modules(mapping, libdir=site_packages)

    assert modules == {
        "pkg": str(src_pkg_dir / "__init__.py"),
        "pkg.module": str(src_pkg_dir / "module.py"),
        "pkg.namespace.module": str(src_pkg_dir / "namespace/module.py"),
        "pkg.subpkg": str(src_pkg_dir / "subpkg/__init__.py"),
        "pkg.subpkg.module": str(src_pkg_dir / "subpkg/module.py"),
        "pkg.resources.file": str(src_pkg_dir / "resources/file.txt"),
    }

    installed = libdir_to_installed(site_packages)
    installed = {k: v for k, v in installed.items() if k.startswith("pkg")}

    assert installed == {
        "pkg.subpkg.source": str(Path("pkg/subpkg/source.py")),
        "pkg.namespace.source": str(Path("pkg/namespace/source.py")),
        "pkg.source": str(Path("pkg/source.py")),
        "pkg.installed_files": str(Path("pkg/installed_files.py")),
        "pkg.iresources.file": str(Path("pkg/iresources/file.txt")),
        "pkg.src_files": str(Path("pkg/src_files.py")),
    }

    editable_txt = editable_redirect(
        modules=modules,
        installed=installed,
        reload_dir=None,
        rebuild=False,
        verbose=False,
        build_options=[],
        install_options=[],
        install_dir="",
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

    # Load resource files
    if sys.version_info >= (3, 9):
        virtualenv.execute("import pkg.src_files")
        virtualenv.execute("import pkg.installed_files")
