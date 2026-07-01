from __future__ import annotations

import importlib.machinery
import sys
import textwrap
from pathlib import Path
from typing import NamedTuple

import pytest

from scikit_build_core.build._editable import (
    collect_search_locations,
    editable_inplace_files,
    editable_redirect,
    editable_redirect_files,
    get_packages,
    libdir_to_installed,
    mapping_to_modules,
)
from scikit_build_core.build._pathutil import (
    is_module,
    is_trackable,
    module_loader_rank,
    packages_to_file_mapping,
)
from scikit_build_core.settings.skbuild_model import ScikitBuildSettings

TYPE_CHECKING = False

if TYPE_CHECKING:
    from conftest import VEnv

# The bare extension-module suffix for this interpreter (.so on Unix, .pyd on
# Windows), and whether .so is importable here (it is not on Windows, where
# versioned-soname collisions cannot occur).
EXT_SUFFIX = importlib.machinery.EXTENSION_SUFFIXES[-1]
SO_IMPORTABLE = ".so" in importlib.machinery.EXTENSION_SUFFIXES
# The stable-ABI suffix for this interpreter, if any: .abi3.so on classic
# builds, .abi3t.so on free-threaded 3.15+, absent on PyPy and free-threaded
# builds without stable-ABI support.
ABI3_SUFFIX = next(
    (s for s in importlib.machinery.EXTENSION_SUFFIXES if s.startswith(".abi3")),
    None,
)


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
        mode="classic",
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

    # Importable modules only: the data file (pkg/resources/file.txt) is not here.
    assert modules == {
        "pkg": str(src_pkg_dir / "__init__.py"),
        "pkg.module": str(src_pkg_dir / "module.py"),
        "pkg.namespace.module": str(src_pkg_dir / "namespace/module.py"),
        "pkg.subpkg": str(src_pkg_dir / "subpkg/__init__.py"),
        "pkg.subpkg.module": str(src_pkg_dir / "subpkg/module.py"),
    }

    installed = libdir_to_installed(site_packages)
    installed = {k: v for k, v in installed.items() if k.startswith("pkg")}

    # Importable modules only: the data file (pkg/iresources/file.txt) is not here.
    assert installed == {
        "pkg.subpkg.source": str(Path("pkg/subpkg/source.py")),
        "pkg.namespace.source": str(Path("pkg/namespace/source.py")),
        "pkg.source": str(Path("pkg/source.py")),
        "pkg.installed_files": str(Path("pkg/installed_files.py")),
        "pkg.src_files": str(Path("pkg/src_files.py")),
    }

    directories, package_names = collect_search_locations(mapping, libdir=site_packages)
    directories = {k: v for k, v in directories.items() if k.startswith("pkg")}
    package_names = [p for p in package_names if p.startswith("pkg")]

    # Data directories are tracked (as directories only, with no importable
    # module) so importlib.resources can reach them: pkg.resources lives in the
    # source tree, pkg.iresources in the install tree.
    assert str(src_pkg_dir / "resources") in directories["pkg.resources"]
    assert "pkg.iresources" in directories
    assert str(src_pkg_dir) in directories["pkg"]
    assert package_names == ["pkg", "pkg.subpkg"]

    editable_txt = editable_redirect(
        modules=modules,
        installed=installed,
        directories=directories,
        packages=package_names,
        reload_dir=None,
        rebuild=False,
        verbose=False,
        build_options=[],
        install_options=[],
        install_dir="",
    )

    site_packages.joinpath("_editable_skbc_pkg.py").write_text(editable_txt)
    site_packages.joinpath("_editable_skbc_pkg.pth").write_text(
        "import _editable_skbc_pkg\n"
    )

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


def test_navigate_editable_remapped_namespace(
    tmp_path: Path, virtualenv: VEnv, monkeypatch: pytest.MonkeyPatch
):
    # Regression test for #1040
    site_packages = virtualenv.purelib

    source_dir = tmp_path / "source"
    source_dir.mkdir()
    monkeypatch.chdir(source_dir)

    # Regular package at its own location ...
    pkg_src = source_dir / "lang" / "pkg"
    pkg_src.mkdir(parents=True)
    pkg_src.joinpath("__init__.py").touch()

    # ... and a namespace subpackage living somewhere unrelated, merged in as
    # pkg.namespace by wheel.packages, holding both a module and a data file.
    extras_src = source_dir / "extras"
    extras_src.mkdir()
    extras_src.joinpath("demo.py").write_text("value = 'remapped'\n")
    extras_src.joinpath("data.txt").write_text("payload")

    modules = {
        "pkg": str(pkg_src / "__init__.py"),
        "pkg.namespace.demo": str(extras_src / "demo.py"),
    }
    directories = {
        "pkg": [str(pkg_src)],
        "pkg.namespace": [str(extras_src)],
    }
    editable_txt = editable_redirect(
        modules=modules,
        installed={},
        directories=directories,
        packages=["pkg"],
        reload_dir=None,
        rebuild=False,
        verbose=False,
        build_options=[],
        install_options=[],
        install_dir="",
    )

    site_packages.joinpath("_editable_skbc_pkg.py").write_text(editable_txt)
    site_packages.joinpath("_editable_skbc_pkg.pth").write_text(
        "import _editable_skbc_pkg\n"
    )

    # Importing the bare namespace package and a module under it must both work.
    virtualenv.execute("import pkg.namespace")
    out = virtualenv.execute(
        "import pkg.namespace.demo; print(pkg.namespace.demo.value)"
    )
    assert out == "remapped"

    # importlib.resources must reach data in the remapped namespace directory.
    if sys.version_info >= (3, 9):
        read_data = (
            "from importlib.resources import files;"
            " print(files('pkg.namespace').joinpath('data.txt').read_text(encoding='utf-8'))"
        )
    else:
        read_data = (
            "from importlib.resources import read_text;"
            " print(read_text('pkg.namespace', 'data.txt'))"
        )
    assert virtualenv.execute(read_data) == "payload"


def test_packages_to_file_mapping_module(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    # A wheel.packages entry may point at a single module file, not just a
    # directory (#888). It is installed as one top-level file.
    (tmp_path / "hello.py").write_text("def run(): ...\n", encoding="utf-8")
    monkeypatch.chdir(tmp_path)

    mapping = packages_to_file_mapping(
        packages={"hello.py": "hello.py"},
        platlib_dir=tmp_path / "out",
        include=[],
        src_exclude=[],
        target_exclude=[],
        build_dir="",
        mode="classic",
    )
    assert mapping == {"hello.py": str(tmp_path / "out" / "hello.py")}


def test_packages_to_file_mapping_module_nested(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    # The table form may place a module under a subpackage path.
    src = tmp_path / "src"
    src.mkdir()
    (src / "hello.py").write_text("def run(): ...\n", encoding="utf-8")
    monkeypatch.chdir(tmp_path)

    mapping = packages_to_file_mapping(
        packages={"pkg/hello.py": str(Path("src/hello.py"))},
        platlib_dir=tmp_path / "out",
        include=[],
        src_exclude=[],
        target_exclude=[],
        build_dir="",
        mode="classic",
    )
    assert mapping == {
        str(Path("src/hello.py")): str(tmp_path / "out" / "pkg" / "hello.py")
    }


def test_packages_to_file_mapping_missing_source(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    # A source that is neither a file nor a directory used to be silently
    # dropped; it must now raise instead (#888).
    monkeypatch.chdir(tmp_path)

    with pytest.raises(FileNotFoundError, match="nope"):
        packages_to_file_mapping(
            packages={"nope": "nope"},
            platlib_dir=tmp_path / "out",
            include=[],
            src_exclude=[],
            target_exclude=[],
            build_dir="",
            mode="classic",
        )


def test_editable_redirect_files_external_install_prefix(tmp_path: Path):
    # A rebuildable editable (#1135) records the install tree as absolute paths
    # and bakes the install prefix as the rebuild --prefix, so imports resolve to
    # the persistent build tree and rebuilds skip the reconfigure.
    import importlib.machinery

    from scikit_build_core.settings.skbuild_model import EditableSettings

    ext = importlib.machinery.EXTENSION_SUFFIXES[0]
    libdir = tmp_path / "build" / "install" / "platlib"
    mod = libdir / "pkg" / f"_module{ext}"
    mod.parent.mkdir(parents=True)
    mod.touch()
    install_prefix = str(libdir)

    files = editable_redirect_files(
        libdir=libdir,
        mapping={},
        name="pkg",
        packages=[],
        reload_dir=tmp_path / "build",
        settings=ScikitBuildSettings(editable=EditableSettings(rebuild=True)),
        use_start=False,
        install_prefix=install_prefix,
    )

    redirect = files["_editable_skbc_pkg.py"].decode()
    # The compiled module is referenced by its absolute build-tree path ...
    assert repr(str(mod)) in redirect
    # ... and the install prefix passed to the redirect is the build tree, not a
    # site-packages-relative value.
    assert repr(install_prefix) in redirect


def test_editable_redirect_files_legacy_pth(tmp_path: Path):
    files = editable_redirect_files(
        libdir=tmp_path,
        mapping={},
        name="pkg",
        packages=[str(tmp_path / "src")],
        reload_dir=None,
        settings=ScikitBuildSettings(),
        use_start=False,
    )

    assert set(files) == {"_editable_skbc_pkg.py", "_editable_skbc_pkg.pth"}
    assert "_editable_skbc_pkg.start" not in files

    pth = files["_editable_skbc_pkg.pth"].decode()
    assert pth.splitlines()[0] == "import _editable_skbc_pkg"
    assert str(tmp_path / "src") in pth

    py = files["_editable_skbc_pkg.py"].decode()
    assert "\ninstall(" in py
    assert "def entrypoint()" not in py


def test_editable_redirect_files_pep829_start(tmp_path: Path):
    files = editable_redirect_files(
        libdir=tmp_path,
        mapping={},
        name="pkg",
        packages=[str(tmp_path / "src")],
        reload_dir=None,
        settings=ScikitBuildSettings(),
        use_start=True,
    )

    assert set(files) == {
        "_editable_skbc_pkg.py",
        "_editable_skbc_pkg.pth",
        "_editable_skbc_pkg.start",
    }

    # PEP 829 mandates UTF-8-sig (BOM) for .start files
    start = files["_editable_skbc_pkg.start"]
    assert start == "_editable_skbc_pkg:entrypoint".encode("utf-8-sig")
    assert start.startswith(b"\xef\xbb\xbf")

    # The .pth keeps only the sys.path entries, no import line
    pth = files["_editable_skbc_pkg.pth"].decode()
    assert "import _editable_skbc_pkg" not in pth
    assert str(tmp_path / "src") in pth

    # The import is now a zero-argument entrypoint, not run at import time
    py = files["_editable_skbc_pkg.py"].decode()
    assert "def entrypoint() -> None:" in py
    assert "\ninstall(" not in py


def test_editable_redirect_files_pep829_no_paths(tmp_path: Path):
    # With no package paths, no .pth file is needed on 3.15+
    files = editable_redirect_files(
        libdir=tmp_path,
        mapping={},
        name="pkg",
        packages=[],
        reload_dir=None,
        settings=ScikitBuildSettings(),
        use_start=True,
    )

    assert set(files) == {"_editable_skbc_pkg.py", "_editable_skbc_pkg.start"}


def test_editable_inplace_files_legacy_pth(tmp_path: Path):
    files = editable_inplace_files(
        name="pkg",
        packages={"pkg": "src/pkg"},
        package_paths=[str(tmp_path / "src")],
        source_dir=tmp_path / "build",
        settings=ScikitBuildSettings(),
        use_start=False,
    )

    assert set(files) == {"_editable_skbc_pkg.py", "_editable_skbc_pkg.pth"}

    pth = files["_editable_skbc_pkg.pth"].decode()
    assert pth.splitlines()[0] == "import _editable_skbc_pkg"
    assert str(tmp_path / "src") in pth

    py = files["_editable_skbc_pkg.py"].decode()
    # Inplace installs the rebuild-only finder, not the redirect one.
    assert "\ninstall_inplace(" in py
    assert "def entrypoint()" not in py
    # The package leaf name is wrapped and the source dir is the rebuild path.
    assert "'pkg'" in py
    assert repr(str(tmp_path / "build")) in py


def test_editable_inplace_files_pep829_start(tmp_path: Path):
    files = editable_inplace_files(
        name="pkg",
        packages={"pkg": "src/pkg"},
        package_paths=[str(tmp_path / "src")],
        source_dir=tmp_path / "build",
        settings=ScikitBuildSettings(),
        use_start=True,
    )

    assert set(files) == {
        "_editable_skbc_pkg.py",
        "_editable_skbc_pkg.pth",
        "_editable_skbc_pkg.start",
    }

    start = files["_editable_skbc_pkg.start"]
    assert start == "_editable_skbc_pkg:entrypoint".encode("utf-8-sig")

    pth = files["_editable_skbc_pkg.pth"].decode()
    assert "import _editable_skbc_pkg" not in pth
    assert str(tmp_path / "src") in pth

    py = files["_editable_skbc_pkg.py"].decode()
    assert "def entrypoint() -> None:" in py
    assert "install_inplace(" in py


def test_editable_inplace_files_module_entry(tmp_path: Path):
    # A wheel.packages entry may point at a single module file (e.g. hello.py,
    # #888). The finder matches fullname.partition(".")[0] (``hello``), so the
    # wrapped name must be the module's import name, not the filename.
    files = editable_inplace_files(
        name="hello",
        packages={"hello.py": "hello.py"},
        package_paths=[str(tmp_path)],
        source_dir=tmp_path,
        settings=ScikitBuildSettings(),
        use_start=False,
    )

    py = files["_editable_skbc_hello.py"].decode()
    # install_inplace's first argument is the known_packages list.
    assert "install_inplace(['hello']," in py
    assert "hello.py" not in py.partition("install_inplace(")[2].partition("]")[0]


def test_editable_inplace_files_bakes_rebuild_flag(tmp_path: Path):
    from scikit_build_core.settings.skbuild_model import EditableSettings

    files = editable_inplace_files(
        name="pkg",
        packages={"pkg": "src/pkg"},
        package_paths=[str(tmp_path / "src")],
        source_dir=tmp_path / "build",
        settings=ScikitBuildSettings(
            editable=EditableSettings(mode="inplace", rebuild=True, verbose=False)
        ),
        use_start=False,
    )

    # install_inplace args: known_packages, search_paths, path, rebuild, verbose,
    # build_options -- so a rebuild-on-import editable bakes ..., True, False, [].
    py = files["_editable_skbc_pkg.py"].decode()
    assert f"{str(tmp_path / 'build')!r}, True, False, []" in py


def test_editable_redirect_files_absolute_install_dir_no_rebuild(tmp_path: Path):
    # Regression test for #909: absolute wheel.install-dir must not block a
    # non-rebuild editable install; only rebuild=True is incompatible.
    from scikit_build_core.settings.skbuild_model import WheelSettings

    settings = ScikitBuildSettings(
        wheel=WheelSettings(install_dir="/data"),
    )
    assert not settings.editable.rebuild  # default

    # Should not raise
    files = editable_redirect_files(
        libdir=tmp_path,
        mapping={},
        name="pkg",
        packages=[],
        reload_dir=None,
        settings=settings,
        use_start=False,
    )
    assert "_editable_skbc_pkg.py" in files


def test_editable_redirect_files_absolute_install_dir_with_rebuild(tmp_path: Path):
    # rebuild=True with an absolute install-dir must still raise AssertionError.
    from scikit_build_core.settings.skbuild_model import EditableSettings, WheelSettings

    settings = ScikitBuildSettings(
        wheel=WheelSettings(install_dir="/data"),
        editable=EditableSettings(rebuild=True),
    )

    with pytest.raises(AssertionError, match=r"non-platlib wheel\.install-dir"):
        editable_redirect_files(
            libdir=tmp_path,
            mapping={},
            name="pkg",
            packages=[],
            reload_dir=None,
            settings=settings,
            use_start=False,
        )


def test_editable_redirect_files_var_install_dir_with_rebuild(tmp_path: Path):
    # A non-platlib ${SKBUILD_*_DIR} install-dir is incompatible with rebuild.
    from scikit_build_core.settings.skbuild_model import EditableSettings, WheelSettings

    settings = ScikitBuildSettings(
        wheel=WheelSettings(install_dir="${SKBUILD_DATA_DIR}/pkg"),
        editable=EditableSettings(rebuild=True),
    )

    with pytest.raises(AssertionError, match=r"non-platlib wheel\.install-dir"):
        editable_redirect_files(
            libdir=tmp_path,
            mapping={},
            name="pkg",
            packages=[],
            reload_dir=None,
            settings=settings,
            use_start=False,
        )


def test_get_packages_explicit_passthrough():
    # An explicit mapping is returned as-is.
    assert get_packages(packages={"ns/pkg": "src/ns/pkg"}, name="ignored") == {
        "ns/pkg": "src/ns/pkg"
    }
    # An explicit sequence is keyed by the final path component.
    assert get_packages(packages=["src/foo", "other/bar"], name="ignored") == {
        "foo": "src/foo",
        "bar": "other/bar",
    }


def test_get_packages_flat_discovery(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    pkg = tmp_path / "src" / "ns_pkg"
    pkg.mkdir(parents=True)
    (pkg / "__init__.py").touch()
    monkeypatch.chdir(tmp_path)

    # The distribution name's separators all normalize to the flat dir name.
    expected = {"ns_pkg": str(Path("src") / "ns_pkg")}
    for name in ("ns-pkg", "ns_pkg", "ns.pkg"):
        assert get_packages(packages=None, name=name) == expected


def test_get_packages_namespace_discovery(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    # PEP 420 namespace package: the namespace dir has no __init__, the leaf does.
    leaf = tmp_path / "src" / "ns" / "pkg"
    leaf.mkdir(parents=True)
    (leaf / "__init__.py").touch()
    monkeypatch.chdir(tmp_path)

    # A '.' marks the namespace boundary and maps to a nested path; a '-' within
    # a component is import-normalized to '_'. The key is a forward-slash rel
    # path, but the discovered source uses the OS-native separator.
    assert get_packages(packages=None, name="ns.pkg") == {
        "ns/pkg": str(Path("src") / "ns" / "pkg")
    }
    assert get_packages(packages=None, name="ns.my-pkg") == {}

    # The flat layout still wins when it exists (back-compat over the namespace).
    flat = tmp_path / "src" / "ns_pkg"
    flat.mkdir()
    (flat / "__init__.py").touch()
    assert get_packages(packages=None, name="ns.pkg") == {
        "ns_pkg": str(Path("src") / "ns_pkg")
    }


def test_get_packages_not_found(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.chdir(tmp_path)
    assert get_packages(packages=None, name="ns.pkg") == {}
    # A namespace dir with no __init__ on the leaf is not a discoverable package.
    (tmp_path / "src" / "ns" / "pkg").mkdir(parents=True)
    assert get_packages(packages=None, name="ns.pkg") == {}


@pytest.mark.parametrize(
    "install_dir", ["${SKBUILD_PLATLIB_DIR}/pkg", "${SKBUILD_PURELIB_DIR}/pkg"]
)
def test_editable_redirect_files_platlib_var_install_dir_with_rebuild(
    tmp_path: Path, install_dir: str
):
    # A platlib/purelib selector resolves to the target lib (equivalent to a
    # plain relative dir), so it stays compatible with rebuild. The shim must get
    # the reduced remainder, not the raw ${...} string.
    from scikit_build_core.settings.skbuild_model import EditableSettings, WheelSettings

    settings = ScikitBuildSettings(
        wheel=WheelSettings(install_dir=install_dir),
        editable=EditableSettings(rebuild=True),
    )

    files = editable_redirect_files(
        libdir=tmp_path,
        mapping={},
        name="pkg",
        packages=[],
        reload_dir=None,
        settings=settings,
        use_start=False,
    )
    shim = files["_editable_skbc_pkg.py"].decode()
    # The reduced remainder is passed; the raw selector never reaches the shim.
    assert "'pkg'" in shim
    assert "SKBUILD_PLATLIB_DIR" not in shim
    assert "SKBUILD_PURELIB_DIR" not in shim


def test_editable_redirect_files_rebuild_dir_implies_rebuild(tmp_path: Path):
    # editable.rebuild-dir turns on rebuild-on-import by itself, so the
    # non-platlib install-dir guard fires even with editable.rebuild left False.
    from scikit_build_core.settings.skbuild_model import EditableSettings, WheelSettings

    settings = ScikitBuildSettings(
        wheel=WheelSettings(install_dir="/data"),
        editable=EditableSettings(rebuild=False, rebuild_dir=str(tmp_path / "tree")),
    )

    with pytest.raises(AssertionError, match=r"non-platlib wheel\.install-dir"):
        editable_redirect_files(
            libdir=tmp_path,
            mapping={},
            name="pkg",
            packages=[],
            reload_dir=None,
            settings=settings,
            use_start=False,
        )


@pytest.mark.parametrize("install_dir", ["/data", "${SKBUILD_DATA_DIR}/pkg"])
def test_editable_redirect_files_nonplatlib_install_dir_no_rebuild_baked_safe(
    tmp_path: Path, install_dir: str
):
    # #1417 Bug A: a non-rebuild editable with a build-dir still exposes a manual
    # module.__loader__.rebuild() (#1403). The raw non-platlib install-dir must
    # NOT be baked into the shim, since the shim does os.path.join(DIR,
    # install_dir): '/data' would install into the filesystem root and
    # '${SKBUILD_DATA_DIR}/pkg' into a literal '${SKBUILD_DATA_DIR}' dir. A None
    # sentinel is baked instead so rebuild() refuses cleanly.
    from scikit_build_core.settings.skbuild_model import WheelSettings

    settings = ScikitBuildSettings(wheel=WheelSettings(install_dir=install_dir))
    assert not settings.editable.rebuild

    files = editable_redirect_files(
        libdir=tmp_path,
        mapping={},
        name="pkg",
        packages=[],
        reload_dir=tmp_path,
        settings=settings,
        use_start=False,
    )
    shim = files["_editable_skbc_pkg.py"].decode()
    # The install() call's last positional arg is install_dir; it must be None.
    call = shim.rpartition("install(")[2]
    assert call.rstrip().endswith("None)")
    assert "${SKBUILD" not in shim


def test_editable_redirect_files_platlib_install_dir_no_rebuild_reduced(
    tmp_path: Path,
):
    # #1417 Bug A: a platlib/purelib selector is reproducible by the shim's
    # platlib-relative join, so even without rebuild it is reduced to its
    # remainder (not baked raw) so a manual rebuild() installs correctly.
    from scikit_build_core.settings.skbuild_model import WheelSettings

    settings = ScikitBuildSettings(
        wheel=WheelSettings(install_dir="${SKBUILD_PLATLIB_DIR}/pkg")
    )
    assert not settings.editable.rebuild

    files = editable_redirect_files(
        libdir=tmp_path,
        mapping={},
        name="pkg",
        packages=[],
        reload_dir=tmp_path,
        settings=settings,
        use_start=False,
    )
    shim = files["_editable_skbc_pkg.py"].decode()
    call = shim.rpartition("install(")[2]
    assert call.rstrip().endswith("'pkg')")
    assert "SKBUILD_PLATLIB_DIR" not in shim


def test_prepare_editable_rebuild_dir_refuses_populated(tmp_path: Path):
    from scikit_build_core.build.common_wheel_helpers import (
        prepare_editable_rebuild_dir,
    )

    # A user-chosen rebuild-dir pointing at populated source must not be wiped.
    source = tmp_path / "python" / "src" / "mypackage"
    source.mkdir(parents=True)
    keep = source / "__init__.py"
    keep.write_text("x = 1\n")

    with pytest.raises(FileExistsError, match="refusing to delete"):
        prepare_editable_rebuild_dir(source, guard=True)

    assert keep.read_text() == "x = 1\n"


def test_prepare_editable_rebuild_dir_refreshes_own_tree(tmp_path: Path):
    from scikit_build_core.build.common_wheel_helpers import (
        CACHEDIR_TAG_NAME,
        prepare_editable_rebuild_dir,
    )

    tree = tmp_path / "rebuild_tree"

    # First build creates the tree with a cache-tag and a .gitignore.
    prepare_editable_rebuild_dir(tree, guard=True)
    tag = tree / CACHEDIR_TAG_NAME
    assert tag.read_text().startswith("Signature: 8a477f597d28d172789f06886806bc55")
    assert (tree / ".gitignore").read_text().endswith("*\n")

    # Stale artifacts from a prior build are wiped on the next build because the
    # cache-tag proves the tree is ours.
    stale = tree / "_module.so"
    stale.write_text("stale\n")
    prepare_editable_rebuild_dir(tree, guard=True)
    assert not stale.exists()
    assert tag.is_file()


def test_prepare_editable_rebuild_dir_default_tree_unguarded(tmp_path: Path):
    from scikit_build_core.build.common_wheel_helpers import (
        CACHEDIR_TAG_NAME,
        prepare_editable_rebuild_dir,
    )

    # The default install/<targetlib> tree lives inside build-dir and is fully
    # owned by scikit-build-core, so it is wiped without the cache-tag guard and
    # no tag/.gitignore is written.
    tree = tmp_path / "build" / "install" / "platlib"
    tree.mkdir(parents=True)
    (tree / "old.so").write_text("old\n")

    prepare_editable_rebuild_dir(tree, guard=False)
    assert not (tree / "old.so").exists()
    assert not (tree / CACHEDIR_TAG_NAME).exists()
    assert not (tree / ".gitignore").exists()


def test_is_trackable():
    # Importable modules and data/resource files are both tracked, so the
    # redirect registers their directories for importlib.resources.
    assert is_trackable(Path("one.py"))
    assert is_trackable(Path("one/two.py"))
    assert is_trackable(Path("one/two.pyc"))
    assert is_trackable(Path("tango/_tango.so"))
    assert is_trackable(Path("tango/_tango.abi3.so"))
    assert is_trackable(Path("pkg/resources/file.txt"))
    assert is_trackable(Path("pkg/module.pyx"))
    assert is_trackable(Path("pkg/module.pxd"))
    # Versioned sonames are tracked too (so tango/ still gets registered), but
    # is_module rejects them so they never resolve as the module (issue #1144).
    assert is_trackable(Path("tango/_tango.so.10"))
    assert is_trackable(Path("tango/_tango.so.10.1.0.0"))

    # Invalid identifiers are rejected
    assert not is_trackable(Path("1one/two.py"))
    assert not is_trackable(Path("one/2two.py"))
    assert not is_trackable(Path("one/.py"))
    assert not is_trackable(Path(".py"))


def test_is_module():
    # Importable module files (EXT_SUFFIX is .so on Unix, .pyd on Windows)
    assert is_module(Path("one.py"))
    assert is_module(Path("one/two.pyc"))
    assert is_module(Path(f"mod{EXT_SUFFIX}"))

    # Data/resource and Cython source files are not importable modules
    assert not is_module(Path("pkg/resources/file.txt"))
    assert not is_module(Path("pkg/module.pyx"))
    assert not is_module(Path("pkg/module.pxd"))


@pytest.mark.skipif(
    not SO_IMPORTABLE, reason="versioned .so sonames only occur where .so is importable"
)
def test_is_module_rejects_versioned_sonames():
    assert is_module(Path("tango/_tango.so"))
    if ABI3_SUFFIX:
        assert is_module(Path(f"tango/_tango{ABI3_SUFFIX}"))

    # Versioned sonames are not importable (PEP 3149); they alias the real
    # _tango.so and must not resolve as the module (issue #1144).
    assert not is_module(Path("tango/_tango.so.10"))
    assert not is_module(Path("tango/_tango.so.10.1.0.0"))


def test_module_loader_rank_matches_import_precedence():
    # Extension modules load before source, source before bytecode; everything
    # else (data, versioned sonames) ranks last. This mirrors Python's own
    # FileFinder order so editable installs resolve the same file as a wheel.
    ext_rank = module_loader_rank(Path(f"mod{EXT_SUFFIX}"))
    py_rank = module_loader_rank(Path("mod.py"))
    pyc_rank = module_loader_rank(Path("mod.pyc"))
    data_rank = module_loader_rank(Path("file.txt"))

    assert ext_rank < py_rank < pyc_rank < data_rank


@pytest.mark.skipif(
    len(importlib.machinery.EXTENSION_SUFFIXES) < 2,
    reason="needs at least two extension suffixes to order",
)
def test_module_loader_rank_orders_extension_suffixes():
    # FileFinder tries EXTENSION_SUFFIXES in order, so a more specific tag (e.g.
    # .cpython-313-...so) outranks the bare suffix (.so) for the same module.
    suffixes = importlib.machinery.EXTENSION_SUFFIXES
    assert module_loader_rank(Path(f"mod{suffixes[0]}")) < module_loader_rank(
        Path(f"mod{suffixes[-1]}")
    )


@pytest.mark.skipif(
    len(importlib.machinery.EXTENSION_SUFFIXES) < 2,
    reason="needs at least two extension suffixes to order",
)
def test_libdir_to_installed_prefers_specific_extension_tag(tmp_path: Path):
    # Two extension files for the same module: pick the one a wheel import would
    # load first (the most specific tag), not whichever was scanned first.
    suffixes = importlib.machinery.EXTENSION_SUFFIXES
    pkg_dir = tmp_path / "pkg"
    pkg_dir.mkdir()
    (pkg_dir / f"mod{suffixes[0]}").touch()
    (pkg_dir / f"mod{suffixes[-1]}").touch()

    installed = libdir_to_installed(tmp_path)

    assert installed["pkg.mod"] == str(Path("pkg") / f"mod{suffixes[0]}")


def test_libdir_to_installed_prefers_extension_over_source(tmp_path: Path):
    # A wheel import loads the extension module before mod.py; editable agrees.
    pkg_dir = tmp_path / "pkg"
    pkg_dir.mkdir()
    (pkg_dir / f"mod{EXT_SUFFIX}").touch()
    (pkg_dir / "mod.py").touch()

    installed = libdir_to_installed(tmp_path)

    assert installed["pkg.mod"] == str(Path("pkg") / f"mod{EXT_SUFFIX}")


@pytest.mark.skipif(
    not SO_IMPORTABLE, reason="versioned .so sonames only occur where .so is importable"
)
def test_libdir_to_installed_prefers_plain_so_over_versioned(tmp_path: Path):
    # Simulate a site-packages/tango/ directory that has all three soname variants,
    # as seen in the pytango issue (#1144). Only _tango.so should be selected.
    pkg_dir = tmp_path / "tango"
    pkg_dir.mkdir()
    (pkg_dir / "_tango.so").touch()
    (pkg_dir / "_tango.so.10").touch()
    (pkg_dir / "_tango.so.10.1.0.0").touch()

    installed = libdir_to_installed(tmp_path)

    assert "tango._tango" in installed
    # Must pick the plain .so, not a versioned soname
    assert installed["tango._tango"] == str(Path("tango/_tango.so"))


def test_collect_search_locations_data_only_install_dir(tmp_path: Path):
    # The source tree has the importable package; the install (CMake) tree adds
    # only a data file into the same package dir. The install dir must still be
    # registered on pkg.__path__ so importlib.resources can find the data --
    # this is the one case where a non-importable file is load-bearing.
    libdir = tmp_path / "site"
    (libdir / "pkg").mkdir(parents=True)
    (libdir / "pkg" / "data.txt").write_text("hi")
    src = tmp_path / "src"
    mapping = {str(src / "pkg" / "__init__.py"): str(libdir / "pkg" / "__init__.py")}

    directories, packages = collect_search_locations(mapping, libdir)

    assert packages == ["pkg"]
    # pkg.__path__ has both the source dir (absolute) and the install dir
    # (relative), the latter reachable only because the data file registered it.
    assert str(src / "pkg") in directories["pkg"]
    assert str(Path("pkg")) in directories["pkg"]
    # The data file itself is not an importable module.
    assert "pkg.data" not in libdir_to_installed(libdir)


def test_collect_search_locations_pxd_packages(tmp_path: Path):
    # .pxd/.pyx __init__ files define packages even though they are not
    # importable; they must be marked as packages and given their own directory
    # without polluting the parent package's __path__.
    libdir = tmp_path / "site"
    libdir.mkdir()
    src = tmp_path / "src"
    mapping = {
        str(src / "pkg" / "__init__.py"): str(libdir / "pkg" / "__init__.py"),
        str(src / "pkg" / "cython_subpkg" / "__init__.pxd"): str(
            libdir / "pkg" / "cython_subpkg" / "__init__.pxd"
        ),
        str(src / "pkg" / "cython_subpkg" / "impl.pyx"): str(
            libdir / "pkg" / "cython_subpkg" / "impl.pyx"
        ),
        str(src / "pkg" / "pyx_subpkg" / "__init__.pyx"): str(
            libdir / "pkg" / "pyx_subpkg" / "__init__.pyx"
        ),
    }

    directories, packages = collect_search_locations(mapping, libdir)

    assert "pkg.cython_subpkg" in packages
    assert "pkg.pyx_subpkg" in packages
    assert directories["pkg.cython_subpkg"] == [str(src / "pkg" / "cython_subpkg")]
    assert directories["pkg.pyx_subpkg"] == [str(src / "pkg" / "pyx_subpkg")]
    # The parent pkg.__path__ must not be polluted with child package dirs.
    assert all("subpkg" not in p for p in directories["pkg"])
