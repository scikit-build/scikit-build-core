import hashlib
import shutil
import subprocess
import sys
import tarfile
import textwrap
import zipfile
from pathlib import Path

import pytest


@pytest.mark.network()
@pytest.mark.integration()
def test_pep518_sdist(package_simple_pyproject_ext):
    correct_metadata = textwrap.dedent(
        """\
        Metadata-Version: 2.1
        Name: cmake-example
        Version: 0.0.1
        Requires-Python: >=3.7
        Provides-Extra: test
        Requires-Dist: pytest>=6.0; extra == "test"
        """
    )

    subprocess.run([sys.executable, "-m", "build", "--sdist"], check=True)
    (sdist,) = Path("dist").iterdir()
    assert sdist.name == "cmake-example-0.0.1.tar.gz"

    if not sys.platform.startswith(("win", "cygwin")):
        hash = hashlib.sha256(sdist.read_bytes()).hexdigest()
        assert hash == package_simple_pyproject_ext.sdist_hash

    with tarfile.open(sdist) as f:
        file_names = set(f.getnames())
        assert file_names == {
            f"cmake-example-0.0.1/{x}"
            for x in (
                "CMakeLists.txt",
                "pyproject.toml",
                "src/main.cpp",
                "PKG-INFO",
                "LICENSE",
            )
        }
        pkg_info = f.extractfile("cmake-example-0.0.1/PKG-INFO")
        assert pkg_info
        pkg_info_contents = pkg_info.read().decode()
        assert correct_metadata == pkg_info_contents


@pytest.mark.compile()
@pytest.mark.configure()
@pytest.mark.integration()
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

    if sys.version_info >= (3, 8):
        with wheel.open("rb") as f:
            p = zipfile.Path(f)
            file_names = [p.name for p in p.iterdir()]
            assert p.joinpath("cmake_example-0.0.1.dist-info/licenses/LICENSE").exists()

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


@pytest.mark.compile()
@pytest.mark.configure()
@pytest.mark.integration()
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

    if sys.version_info >= (3, 8):
        with wheel.open("rb") as f:
            p = zipfile.Path(f)
            file_names = [p.name for p in p.iterdir()]
            assert p.joinpath("cmake_example-0.0.1.dist-info/licenses/LICENSE").exists()

        assert len(file_names) == 2
        assert "cmake_example-0.0.1.dist-info" in file_names
        file_names.remove("cmake_example-0.0.1.dist-info")
        (so_file,) = file_names

        assert so_file.startswith("cmake_example")
        print("SOFILE:", so_file)

    isolated.install(wheel)

    version = isolated.execute("import cmake_example; print(cmake_example.__version__)")
    assert version == "0.0.1"


@pytest.mark.compile()
@pytest.mark.configure()
@pytest.mark.integration()
@pytest.mark.usefixtures("package_simple_pyproject_ext")
def test_pep518_pip(isolated):
    isolated.install("-v", ".")

    version = isolated.execute("import cmake_example; print(cmake_example.__version__)")
    assert version == "0.0.1"

    add = isolated.execute("import cmake_example; print(cmake_example.add(1, 2))")
    assert add == "3"
