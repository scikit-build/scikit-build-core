import hashlib
import shutil
import subprocess
import sys
import tarfile
import textwrap
import zipfile
from pathlib import Path

import pytest

DIR = Path(__file__).parent.resolve()
HELLO_PEP518 = DIR / "packages/simple_pyproject_ext"


@pytest.mark.isolated()
@pytest.mark.integration()
def test_pep518_sdist():
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

    dist = HELLO_PEP518 / "dist"
    shutil.rmtree(dist, ignore_errors=True)
    subprocess.run(
        [sys.executable, "-m", "build", "--sdist"], cwd=HELLO_PEP518, check=True
    )
    (sdist,) = dist.iterdir()
    assert sdist.name == "cmake-example-0.0.1.tar.gz"

    if not (sys.platform.startswith("win32") or sys.platform.startswith("cygwin")):
        hash = hashlib.sha256(sdist.read_bytes()).hexdigest()
        if sys.version_info < (3, 9):
            assert (
                hash
                == "3b4af3fbe3d4505415bb1e55bb2e49902f4633d371ae7288007d90eb1488bc4d"
            )
        else:
            assert (
                hash
                == "d373b8458ee37b176cfd03f0f3199b30fdb034bca465b2826392a6c3af85ca4c"
            )

    with tarfile.open(sdist) as f:
        file_names = set(f.getnames())
        assert file_names == {
            f"cmake-example-0.0.1/{x}"
            for x in (
                "CMakeLists.txt",
                "pyproject.toml",
                "src/main.cpp",
                "PKG-INFO",
            )
        }
        pkg_info = f.extractfile("cmake-example-0.0.1/PKG-INFO")
        assert pkg_info
        pkg_info_contents = pkg_info.read().decode()
        assert correct_metadata == pkg_info_contents


@pytest.mark.compile()
@pytest.mark.configure()
@pytest.mark.integration()
@pytest.mark.parametrize(
    "build_args", [(), ("--wheel",)], ids=["sdist_to_wheel", "wheel_directly"]
)
def test_pep518_wheel(isolated, build_args, monkeypatch):
    dist = HELLO_PEP518 / "dist"
    shutil.rmtree(dist, ignore_errors=True)
    monkeypatch.chdir(HELLO_PEP518)
    isolated.install("build[virtualenv]")
    isolated.module(
        "build",
        "--config-setting=logging.level=DEBUG",
        *build_args,
    )
    (wheel,) = dist.glob("cmake_example-0.0.1-*.whl")

    if sys.version_info >= (3, 8):
        with wheel.open("rb") as f:
            p = zipfile.Path(f)
            file_names = [p.name for p in p.iterdir()]

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
def test_pep518_rebuild_build_dir(isolated, monkeypatch, tmp_path, build_args):
    dist = HELLO_PEP518 / "dist"
    monkeypatch.chdir(HELLO_PEP518)
    isolated.install("build[virtualenv]")

    build_dir = tmp_path.joinpath("build")
    build_dir.mkdir()
    build_dir = build_dir.resolve()

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
def test_pep518_pip(isolated):
    isolated.install("-v", HELLO_PEP518)

    version = isolated.execute("import cmake_example; print(cmake_example.__version__)")
    assert version == "0.0.1"

    add = isolated.execute("import cmake_example; print(cmake_example.add(1, 2))")
    assert add == "3"
