import importlib.metadata
import tarfile
import textwrap
import zipfile
from pathlib import Path

import pytest
from packaging.version import Version

from scikit_build_core.setuptools import build_meta as setuptools_build_meta
from scikit_build_core.setuptools.build_meta import build_sdist, build_wheel

try:
    from vcs_versioning.overrides import GlobalOverrides
except ImportError:  # pragma: no cover - setuptools-scm < 10 or missing dependency
    GlobalOverrides = None

pytestmark = pytest.mark.setuptools
setuptools_version = Version(importlib.metadata.version("setuptools"))
build_editable = getattr(setuptools_build_meta, "build_editable", None)


@pytest.fixture(autouse=True)
def setuptools_scm_overrides():
    if GlobalOverrides is None:
        yield
        return

    with GlobalOverrides.from_env("SETUPTOOLS_SCM"):
        yield


@pytest.mark.parametrize("package", ["simple_setuptools_ext"], indirect=True)
@pytest.mark.usefixtures("package")
def test_pep517_sdist(tmp_path: Path):
    correct_metadata = textwrap.dedent(
        """\
        Name: cmake-example
        Version: 0.0.1
        Requires-Python: >=3.8
        Provides-Extra: test
        """
        # TODO: why is this missing?
        # Requires-Dist: pytest>=6.0; extra == "test"
        # This was removed in https://github.com/pypa/setuptools/pull/4698 as part of 2.2 support:
        # Metadata-Version: 2.1
    )
    metadata_set = set(correct_metadata.strip().splitlines())

    dist = tmp_path / "dist"
    out = build_sdist(str(dist))

    (sdist,) = dist.iterdir()
    sdist = sdist.resolve()  # Windows mingw64 and UCRT now requires this
    assert sdist.name in {"cmake-example-0.0.1.tar.gz", "cmake_example-0.0.1.tar.gz"}
    assert sdist == dist / out
    cmake_example = sdist.name[:13]

    with tarfile.open(sdist) as f:
        file_names = set(f.getnames())
        assert file_names == {
            f"{cmake_example}-0.0.1/{x}"
            for x in (
                # TODO: "CMakeLists.txt",
                "PKG-INFO",
                "src",
                "src/cmake_example.egg-info",
                "src/cmake_example.egg-info/PKG-INFO",
                "src/cmake_example.egg-info/SOURCES.txt",
                "src/cmake_example.egg-info/dependency_links.txt",
                "src/cmake_example.egg-info/not-zip-safe",
                "src/cmake_example.egg-info/requires.txt",
                "src/cmake_example.egg-info/top_level.txt",
                "pyproject.toml",
                "setup.cfg",
                "setup.py",
                "LICENSE",
                # TODO: "src/main.cpp",
            )
        } | {f"{cmake_example}-0.0.1"}
        pkg_info = f.extractfile(f"{cmake_example}-0.0.1/PKG-INFO")
        assert pkg_info
        pkg_info_contents = set(pkg_info.read().decode().strip().splitlines())
        assert metadata_set <= pkg_info_contents


@pytest.mark.compile
@pytest.mark.configure
@pytest.mark.broken_on_urct
@pytest.mark.parametrize("package", ["simple_setuptools_ext"], indirect=True)
@pytest.mark.usefixtures("package", "pybind11")
def test_pep517_wheel(virtualenv, tmp_path: Path):
    dist = tmp_path / "dist"
    out = build_wheel(str(dist))
    (wheel,) = dist.glob("cmake_example-0.0.1-*.whl")
    wheel = wheel.resolve()  # Windows mingw64 and UCRT now requires this
    assert wheel == dist / out

    with zipfile.ZipFile(wheel) as zf:
        file_names = {Path(n).parts[0] for n in zf.namelist()}

    assert len(file_names) == 2
    assert "cmake_example-0.0.1.dist-info" in file_names
    file_names.remove("cmake_example-0.0.1.dist-info")
    (so_file,) = file_names

    assert so_file.startswith("cmake_example")
    print("SOFILE:", so_file)

    virtualenv.install(wheel)

    version = virtualenv.execute(
        "import cmake_example; print(cmake_example.__version__)"
    )
    assert version.strip() == "0.0.1"

    add = virtualenv.execute("import cmake_example; print(cmake_example.add(1, 2))")
    assert add.strip() == "3"


@pytest.mark.compile
@pytest.mark.configure
@pytest.mark.broken_on_urct
@pytest.mark.skipif(
    build_editable is None, reason="Requires setuptools editable support"
)
@pytest.mark.parametrize("package", ["simple_setuptools_ext"], indirect=True)
@pytest.mark.usefixtures("package", "pybind11")
def test_pep517_editable(virtualenv, tmp_path: Path):
    assert build_editable is not None
    dist = tmp_path / "dist"
    out = build_editable(str(dist))
    (wheel,) = dist.glob("cmake_example-0.0.1-0.editable-*.whl")
    wheel = wheel.resolve()  # Windows mingw64 and UCRT now requires this
    assert wheel == dist / out

    with zipfile.ZipFile(wheel) as zf:
        file_names = {Path(n).parts[0] for n in zf.namelist()}

    assert file_names == {
        "__editable__.cmake_example-0.0.1.pth",
        "cmake_example-0.0.1.dist-info",
    }

    virtualenv.install(wheel)

    module_dir = virtualenv.execute(
        "import pathlib, cmake_example; print(pathlib.Path(cmake_example.__file__).resolve().parent)"
    )
    assert Path(module_dir) == Path("src").resolve()

    version = virtualenv.execute(
        "import cmake_example; print(cmake_example.__version__)"
    )
    assert version.strip() == "0.0.1"

    add = virtualenv.execute("import cmake_example; print(cmake_example.add(1, 2))")
    assert add.strip() == "3"


@pytest.mark.parametrize("package", ["toml_setuptools_ext"], indirect=True)
@pytest.mark.usefixtures("package")
@pytest.mark.skipif(
    setuptools_version < Version("61.0"), reason="Requires setuptools 61+"
)
def test_toml_sdist(tmp_path: Path):
    correct_metadata = textwrap.dedent(
        """\
        Name: cmake-example
        Version: 0.0.1
        Requires-Python: >=3.8
        """
        # This was removed in https://github.com/pypa/setuptools/pull/4698 as part of 2.2 support:
        # Metadata-Version: 2.1
    )
    metadata_set = set(correct_metadata.strip().splitlines())

    dist = tmp_path / "dist"
    out = build_sdist(str(dist))

    (sdist,) = dist.iterdir()
    sdist = sdist.resolve()  # Windows mingw64 and UCRT now requires this
    assert sdist.name in {"cmake-example-0.0.1.tar.gz", "cmake_example-0.0.1.tar.gz"}
    assert sdist == dist / out
    cmake_example = sdist.name[:13]

    with tarfile.open(sdist) as f:
        file_names = set(f.getnames())
        assert file_names == {
            f"{cmake_example}-0.0.1/{x}"
            for x in (
                # TODO: "CMakeLists.txt",
                "PKG-INFO",
                "src",
                "src/cmake_example.egg-info",
                "src/cmake_example.egg-info/PKG-INFO",
                "src/cmake_example.egg-info/SOURCES.txt",
                "src/cmake_example.egg-info/dependency_links.txt",
                "src/cmake_example.egg-info/top_level.txt",
                "pyproject.toml",
                "setup.cfg",
                "LICENSE",
                # TODO: "src/main.cpp",
            )
        } | {f"{cmake_example}-0.0.1"}
        pkg_info = f.extractfile(f"{cmake_example}-0.0.1/PKG-INFO")
        assert pkg_info
        pkg_info_contents = set(pkg_info.read().decode().strip().splitlines())
        assert metadata_set <= pkg_info_contents


@pytest.mark.compile
@pytest.mark.configure
@pytest.mark.parametrize("package", ["toml_setuptools_ext"], indirect=True)
@pytest.mark.usefixtures("package", "pybind11")
@pytest.mark.skipif(
    setuptools_version < Version("61.0"), reason="Requires setuptools 61+"
)
def test_toml_wheel(virtualenv, tmp_path: Path):
    dist = tmp_path / "dist"
    out = build_wheel(str(dist))
    (wheel,) = dist.glob("cmake_example-0.0.1-*.whl")
    wheel = wheel.resolve()  # Windows mingw64 and UCRT now requires this
    assert wheel == dist / out

    with zipfile.ZipFile(wheel) as zf:
        file_names = {Path(n).parts[0] for n in zf.namelist()}

    assert len(file_names) == 2
    assert "cmake_example-0.0.1.dist-info" in file_names
    file_names.remove("cmake_example-0.0.1.dist-info")
    (so_file,) = file_names

    assert so_file.startswith("cmake_example")
    print("SOFILE:", so_file)

    virtualenv.install(wheel)

    version = virtualenv.execute(
        "import cmake_example; print(cmake_example.__version__)"
    )
    assert version.strip() == "0.0.1"

    add = virtualenv.execute("import cmake_example; print(cmake_example.add(1, 2))")
    assert add.strip() == "3"


@pytest.mark.compile
@pytest.mark.configure
@pytest.mark.parametrize("package", ["mixed_setuptools"], indirect=True)
@pytest.mark.usefixtures("package", "pybind11")
def test_mixed_wheel(virtualenv, tmp_path: Path):
    dist = tmp_path / "dist"
    out = build_wheel(str(dist))
    (wheel,) = dist.glob("mixed_setuptools-3.1.4-*.whl")
    wheel = wheel.resolve()  # Windows mingw64 and UCRT now requires this
    assert wheel == dist / out

    with zipfile.ZipFile(wheel) as zf:
        file_names = {Path(n).parts[0] for n in zf.namelist()}

    assert len(file_names) == 2
    assert "mixed_setuptools-3.1.4.dist-info" in file_names
    file_names.remove("mixed_setuptools-3.1.4.dist-info")
    (so_file,) = file_names

    assert so_file.startswith("mixed_setuptools")
    print("SOFILE:", so_file)

    virtualenv.install(wheel)

    add = virtualenv.execute(
        "import mixed_setuptools; print(mixed_setuptools.add(1, 2))"
    )
    assert add.strip() == "3"


@pytest.mark.compile
@pytest.mark.configure
@pytest.mark.parametrize("package", ["plugin_setuptools_install_dir"], indirect=True)
@pytest.mark.usefixtures("package", "pybind11")
def test_plugin_cmake_install_dir_wheel(virtualenv, tmp_path: Path):
    dist = tmp_path / "dist"
    out = build_wheel(str(dist))
    wheel = (dist / out).resolve()
    assert wheel.name.startswith("plugin_example-0.0.1-")

    with zipfile.ZipFile(wheel) as zf:
        file_names = set(zf.namelist())

    assert "plugin_example/__init__.py" in file_names
    assert any(name.startswith("plugin_example/_core.") for name in file_names)

    virtualenv.install(wheel)

    add = virtualenv.execute("import plugin_example; print(plugin_example.add(1, 2))")
    assert add.strip() == "3"


@pytest.mark.compile
@pytest.mark.configure
@pytest.mark.parametrize("package", ["wrapper_setuptools_install_dir"], indirect=True)
@pytest.mark.usefixtures("package", "pybind11")
def test_wrapper_cmake_install_dir_wheel(virtualenv, tmp_path: Path):
    dist = tmp_path / "dist"
    out = build_wheel(str(dist))
    wheel = (dist / out).resolve()
    assert wheel.name.startswith("wrapper_example-0.0.1-")

    with zipfile.ZipFile(wheel) as zf:
        file_names = set(zf.namelist())

    assert "wrapper_example/__init__.py" in file_names
    assert "src/wrapper_example/__init__.py" not in file_names
    assert any(name.startswith("wrapper_example/_core.") for name in file_names)

    virtualenv.install(wheel)

    add = virtualenv.execute("import wrapper_example; print(wrapper_example.add(1, 2))")
    assert add.strip() == "3"
