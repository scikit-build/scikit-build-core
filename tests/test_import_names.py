from __future__ import annotations

import email.parser
import tarfile
import zipfile
from pathlib import Path, PurePosixPath

import pytest

from scikit_build_core._compat.builtins import ExceptionGroup
from scikit_build_core.build import (
    build_editable,
    build_sdist,
    build_wheel,
    prepare_metadata_for_build_wheel,
)
from scikit_build_core.build._import_names import find_import_names

PYPROJECT = """\
[build-system]
requires = ["scikit-build-core"]
build-backend = "scikit_build_core.build"

[project]
name = "pkg"
version = "0.1.0"
dynamic = {dynamic}
{project_extra}

[tool.scikit-build]
wheel.cmake = false
sdist.cmake = false
wheel.packages = ["src/pkg", "src/ns"]
"""


def _find(*paths: str) -> tuple[list[str], list[str]]:
    return find_import_names(PurePosixPath(p) for p in paths)


def test_find_import_names_modules() -> None:
    assert _find(
        "a.py",
        "b.cpython-313-darwin.so",
        "c.abi3.so",
        "d.cp313-win_amd64.pyd",
        "e.pyi",
        "libf.dylib",
        "not-valid.py",
        "class.py",
        "README.txt",
    ) == (["a", "b", "c", "d"], [])


def test_find_import_names_packages() -> None:
    assert _find(
        "pkg/__init__.py",
        "pkg/sub/__init__.py",
        "ext/__init__.cpython-313-x86_64-linux-gnu.so",
        "pkg.libs/libfoo.so",
        "data/file.txt",
        "__pycache__/x.cpython-313.pyc",
    ) == (["ext", "pkg"], [])


def test_find_import_names_namespaces() -> None:
    assert _find(
        "ns/a/__init__.py",
        "ns/b.py",
        "deep/er/pkg/__init__.py",
        "shadow.py",
        "shadow/x.py",
    ) == (
        ["deep.er.pkg", "ns.a", "ns.b", "shadow", "shadow.x"],
        ["deep", "deep.er", "ns"],
    )


def make_pkg(root: Path, dynamic: str, project_extra: str = "") -> None:
    for path in (
        "src/pkg/__init__.py",
        "src/pkg/data.txt",
        "src/ns/sub/__init__.py",
        "src/ns/mod.py",
    ):
        (root / path).parent.mkdir(parents=True, exist_ok=True)
        (root / path).touch()
    (root / "pyproject.toml").write_text(
        PYPROJECT.format(dynamic=dynamic, project_extra=project_extra)
    )


def read_metadata(dist: Path) -> email.message.Message:
    (wheel,) = dist.glob("pkg-0.1.0-*.whl")
    with zipfile.ZipFile(wheel) as zf:
        return email.parser.BytesParser().parsebytes(
            zf.read("pkg-0.1.0.dist-info/METADATA")
        )


def assert_computed(metadata: email.message.Message) -> None:
    assert metadata["Metadata-Version"] == "2.5"
    assert metadata.get_all("Import-Name") == ["ns.mod", "ns.sub", "pkg"]
    assert metadata.get_all("Import-Namespace") == ["ns"]
    assert metadata.get_all("Dynamic") is None


@pytest.fixture
def chdir_tmp(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Path:
    root = tmp_path / "proj"
    root.mkdir()
    monkeypatch.chdir(root)
    return root


@pytest.mark.parametrize("editable", [False, True], ids=["wheel", "editable"])
def test_dynamic_import_names(chdir_tmp: Path, editable: bool) -> None:
    make_pkg(chdir_tmp, '["import-names", "import-namespaces"]')
    dist = chdir_tmp / "dist"
    (build_editable if editable else build_wheel)(str(dist))

    metadata = read_metadata(dist)
    assert_computed(metadata)


def test_dynamic_import_names_extends_static(chdir_tmp: Path) -> None:
    make_pkg(
        chdir_tmp,
        '["import-names"]',
        'import-names = ["pkg; private", "other"]\nimport-namespaces = ["ns"]',
    )
    dist = chdir_tmp / "dist"
    build_wheel(str(dist))

    metadata = read_metadata(dist)
    assert metadata.get_all("Import-Name") == [
        "pkg; private",
        "other",
        "ns.mod",
        "ns.sub",
    ]
    assert metadata.get_all("Import-Namespace") == ["ns"]


def test_dynamic_import_names_needs_namespaces(chdir_tmp: Path) -> None:
    make_pkg(chdir_tmp, '["import-names"]')
    with pytest.raises(ExceptionGroup):
        build_wheel(str(chdir_tmp / "dist"))


def test_dynamic_import_names_sdist(chdir_tmp: Path) -> None:
    make_pkg(chdir_tmp, '["import-names", "import-namespaces"]')
    dist = chdir_tmp / "dist"
    out = build_sdist(str(dist))

    with tarfile.open(dist / out) as tf:
        pkg_info = tf.extractfile("pkg-0.1.0/PKG-INFO")
        assert pkg_info is not None
        metadata = email.parser.BytesParser().parsebytes(pkg_info.read())
    assert_computed(metadata)


def test_dynamic_import_names_prepare_metadata(chdir_tmp: Path) -> None:
    make_pkg(chdir_tmp, '["import-names", "import-namespaces"]')
    out = prepare_metadata_for_build_wheel(str(chdir_tmp / "meta"))

    metadata = email.parser.BytesParser().parsebytes(
        (chdir_tmp / "meta" / out / "METADATA").read_bytes()
    )
    assert_computed(metadata)


def test_dynamic_import_names_default_package(chdir_tmp: Path) -> None:
    make_pkg(chdir_tmp, '["import-names"]')
    pyproject = chdir_tmp / "pyproject.toml"
    pyproject.write_text(
        pyproject.read_text().replace('wheel.packages = ["src/pkg", "src/ns"]\n', "")
    )
    dist = chdir_tmp / "dist"
    build_wheel(str(dist))

    assert read_metadata(dist).get_all("Import-Name") == ["pkg"]


def test_dynamic_import_names_wheel_exclude_single_file(chdir_tmp: Path) -> None:
    make_pkg(chdir_tmp, '["import-names", "import-namespaces"]')
    (chdir_tmp / "src/single.py").touch()
    pyproject = chdir_tmp / "pyproject.toml"
    pyproject.write_text(
        pyproject.read_text().replace(
            '"src/ns"]', '"src/ns", "src/single.py"]\nwheel.exclude = ["mod.py"]'
        )
    )
    dist = chdir_tmp / "dist"
    build_wheel(str(dist))

    metadata = read_metadata(dist)
    assert metadata.get_all("Import-Name") == ["ns.sub", "pkg", "single"]
    assert metadata.get_all("Import-Namespace") == ["ns"]


def test_dynamic_import_names_plugin(chdir_tmp: Path) -> None:
    make_pkg(chdir_tmp, '["import-names", "import-namespaces"]')
    (chdir_tmp / "plugins_import_names").mkdir()
    (chdir_tmp / "plugins_import_names/names.py").write_text(
        "def dynamic_metadata(settings, project):\n"
        "    return {'import-names': ['pkg', 'ns.custom']}\n"
    )
    with (chdir_tmp / "pyproject.toml").open("a") as f:
        f.write(
            '\n[[tool.dynamic-metadata]]\nprovider = {path = "plugins_import_names", module = "names"}\n'
        )
    dist = chdir_tmp / "dist"
    build_wheel(str(dist))

    # The plugin owns import-names; import-namespaces is still computed
    metadata = read_metadata(dist)
    assert metadata.get_all("Import-Name") == ["pkg", "ns.custom"]
    assert metadata.get_all("Import-Namespace") == ["ns"]
