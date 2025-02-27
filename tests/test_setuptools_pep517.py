import importlib.metadata
import tarfile
import textwrap
import zipfile
from pathlib import Path

import pytest
from packaging.version import Version

from scikit_build_core.setuptools.build_meta import build_sdist, build_wheel

pytestmark = pytest.mark.setuptools
setuptools_version = Version(importlib.metadata.version("setuptools"))


@pytest.mark.usefixtures("package_simple_setuptools_ext")
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
@pytest.mark.usefixtures("package_simple_setuptools_ext")
def test_pep517_wheel(virtualenv, tmp_path: Path):
    dist = tmp_path / "dist"
    out = build_wheel(str(dist))
    (wheel,) = dist.glob("cmake_example-0.0.1-*.whl")
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


@pytest.mark.usefixtures("package_toml_setuptools_ext")
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
@pytest.mark.usefixtures("package_toml_setuptools_ext")
@pytest.mark.skipif(
    setuptools_version < Version("61.0"), reason="Requires setuptools 61+"
)
def test_toml_wheel(virtualenv, tmp_path: Path):
    dist = tmp_path / "dist"
    out = build_wheel(str(dist))
    (wheel,) = dist.glob("cmake_example-0.0.1-*.whl")
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
@pytest.mark.usefixtures("package_mixed_setuptools")
def test_mixed_wheel(virtualenv, tmp_path: Path):
    dist = tmp_path / "dist"
    out = build_wheel(str(dist))
    (wheel,) = dist.glob("mixed_setuptools-3.1.4-*.whl")
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
