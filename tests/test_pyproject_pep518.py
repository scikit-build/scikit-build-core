import gzip
import hashlib
import shutil
import sys
import tarfile
import textwrap
import zipfile
from pathlib import Path

import pytest


@pytest.fixture
def cleanup_overwrite():
    overwrite = Path("overwrite.cmake")
    yield overwrite
    if overwrite.exists():
        overwrite.unlink()


def compute_uncompressed_hash(inp: Path):
    with gzip.open(inp, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


@pytest.mark.network
@pytest.mark.integration
def test_pep518_sdist(isolated, package_simple_pyproject_ext):
    correct_metadata = textwrap.dedent(
        """\
        Metadata-Version: 2.1
        Name: CMake.Example
        Version: 0.0.1
        Requires-Python: >=3.7
        Provides-Extra: test
        Requires-Dist: pytest>=6.0; extra == "test"

        """
    )

    isolated.install("build[virtualenv]")
    isolated.module("build", "--sdist")
    (sdist,) = Path("dist").iterdir()
    assert sdist.name == "cmake_example-0.0.1.tar.gz"

    if not sys.platform.startswith(("win", "cygwin")):
        hash = compute_uncompressed_hash(sdist)
        assert hash == package_simple_pyproject_ext.sdist_hash

    with tarfile.open(sdist) as f:
        file_names = set(f.getnames())
        assert file_names == {
            f"cmake_example-0.0.1/{x}"
            for x in (
                "CMakeLists.txt",
                "pyproject.toml",
                "src/main.cpp",
                "PKG-INFO",
                "LICENSE",
            )
        }
        pkg_info = f.extractfile("cmake_example-0.0.1/PKG-INFO")
        assert pkg_info
        pkg_info_contents = pkg_info.read().decode()
        assert correct_metadata == pkg_info_contents


@pytest.mark.network
@pytest.mark.configure
@pytest.mark.integration
@pytest.mark.usefixtures("package_sdist_config")
def test_pep518_sdist_with_cmake_config(isolated, cleanup_overwrite):
    cleanup_overwrite.write_text("set(MY_VERSION fiddlesticks)")

    correct_metadata = textwrap.dedent(
        """\
        Metadata-Version: 2.1
        Name: sdist_config
        Version: 0.1.0

        """
    )

    isolated.install("build[virtualenv]")
    isolated.module("build", "--sdist")
    (sdist,) = Path("dist").iterdir()
    assert sdist.name == "sdist_config-0.1.0.tar.gz"

    with tarfile.open(sdist) as f:
        file_names = set(f.getnames())
        assert file_names > {
            f"sdist_config-0.1.0/{x}"
            for x in (
                "CMakeLists.txt",
                "pyproject.toml",
                "main.cpp",
                "PKG-INFO",
                "overwrite.cmake",
                ".gitignore",
            )
        }
        assert sum("pybind11" in x for x in file_names) >= 10
        pkg_info = f.extractfile("sdist_config-0.1.0/PKG-INFO")
        assert pkg_info
        pkg_info_contents = pkg_info.read().decode()
        assert correct_metadata == pkg_info_contents

    assert cleanup_overwrite.is_file()


@pytest.mark.network
@pytest.mark.compile
@pytest.mark.configure
@pytest.mark.integration
@pytest.mark.usefixtures("package_sdist_config")
@pytest.mark.parametrize(
    "build_args", [(), ("--wheel",)], ids=["sdist_to_wheel", "wheel_directly"]
)
def test_pep518_wheel_sdist_with_cmake_config(
    isolated, build_args, capfd, cleanup_overwrite
):
    isolated.install("build[virtualenv]")
    isolated.module(
        "build",
        "--config-setting=logging.level=DEBUG",
        *build_args,
    )
    out, err = capfd.readouterr()
    if not sys.platform.startswith("win32"):
        assert "Cloning into 'pybind11'..." in err
        if build_args:
            assert "Using integrated pybind11" not in out
        else:
            assert "Using integrated pybind11" in out

    (wheel,) = Path("dist").glob("sdist_config-0.1.0-*.whl")

    with zipfile.ZipFile(wheel) as zf:
        file_names = {Path(n).parts[0] for n in zf.namelist()}

    assert len(file_names) == 3
    file_names.remove("sdist_config-0.1.0.dist-info")
    file_names.remove("output.py")
    (so_file,) = file_names

    assert so_file.startswith("sdist_config")
    print("SOFILE:", so_file)

    isolated.install(wheel)

    life = isolated.execute("import sdist_config; print(sdist_config.life())")
    assert life == "42"

    version = isolated.execute("import output; print(output.version)")
    assert version == "0.1.0"

    assert cleanup_overwrite.is_file()


@pytest.mark.network
@pytest.mark.compile
@pytest.mark.configure
@pytest.mark.integration
@pytest.mark.usefixtures("package_simple_pyproject_ext")
@pytest.mark.parametrize(
    "build_args", [(), ("--wheel",)], ids=["sdist_to_wheel", "wheel_directly"]
)
def test_pep518_wheel(isolated, build_args):
    isolated.install("build[virtualenv]")
    isolated.module(
        "build",
        "--config-setting=logging.level=DEBUG",
        *build_args,
    )
    (wheel,) = Path("dist").glob("cmake_example-0.0.1-*.whl")

    with zipfile.ZipFile(wheel) as zf:
        file_paths = {Path(n) for n in zf.namelist()}
    file_names = {p.parts[0] for p in file_paths}

    assert Path("cmake_example-0.0.1.dist-info/licenses/LICENSE") in file_paths

    assert len(file_names) == 2
    assert "cmake_example-0.0.1.dist-info" in file_names
    file_names.remove("cmake_example-0.0.1.dist-info")
    (so_file,) = file_names

    assert so_file.startswith("cmake_example")
    print("SOFILE:", so_file)

    isolated.install(wheel)

    version = isolated.execute("import cmake_example; print(cmake_example.__version__)")
    assert version == "0.0.1"

    add = isolated.execute("import cmake_example; print(cmake_example.add(1, 2))")
    assert add == "3"


@pytest.mark.network
@pytest.mark.compile
@pytest.mark.configure
@pytest.mark.integration
@pytest.mark.parametrize(
    "build_args", [(), ("--wheel",)], ids=["sdist_to_wheel", "wheel_directly"]
)
@pytest.mark.usefixtures("package_simple_pyproject_ext")
def test_pep518_rebuild_build_dir(isolated, tmp_path, build_args):
    isolated.install("build[virtualenv]")

    build_dir = tmp_path.joinpath("build")
    build_dir.mkdir()
    build_dir = build_dir.resolve()

    dist = Path("dist")

    for _ in range(2):
        shutil.rmtree(dist, ignore_errors=True)
        isolated.module(
            "build",
            *build_args,
            "--config-setting=logging.level=DEBUG",
            f"--config-setting=build-dir={build_dir}",
        )
    (wheel,) = dist.glob("cmake_example-0.0.1-*.whl")

    with zipfile.ZipFile(wheel) as zf:
        file_paths = {Path(p) for p in zf.namelist()}
        file_names = {p.parts[0] for p in file_paths}

    assert Path("cmake_example-0.0.1.dist-info/licenses/LICENSE") in file_paths

    assert len(file_names) == 2
    assert "cmake_example-0.0.1.dist-info" in file_names
    file_names.remove("cmake_example-0.0.1.dist-info")
    (so_file,) = file_names

    assert so_file.startswith("cmake_example")
    print("SOFILE:", so_file)

    isolated.install(wheel)

    version = isolated.execute("import cmake_example; print(cmake_example.__version__)")
    assert version == "0.0.1"


@pytest.mark.network
@pytest.mark.compile
@pytest.mark.configure
@pytest.mark.integration
@pytest.mark.usefixtures("package_simple_pyproject_ext")
def test_pep518_pip(isolated):
    isolated.install("-v", ".")

    version = isolated.execute("import cmake_example; print(cmake_example.__version__)")
    assert version == "0.0.1"

    add = isolated.execute("import cmake_example; print(cmake_example.add(1, 2))")
    assert add == "3"
