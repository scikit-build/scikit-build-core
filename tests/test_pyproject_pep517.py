import hashlib
import shutil
import sys
import tarfile
import time
import zipfile
from pathlib import Path

import pytest

from scikit_build_core.build import build_sdist, build_wheel

DIR = Path(__file__).parent.resolve()
HELLO_PEP518 = DIR / "packages/simple_pyproject_ext"
ENTRYPOINTS = """\
[one.two]
three = four

[console_scripts]
something = other

[gui_scripts]
guithing = a.b:c
"""
METADATA = """\
Metadata-Version: 2.1
Name: cmake-example
Version: 0.0.1
Requires-Python: >=3.7
Provides-Extra: test
Requires-Dist: pytest>=6.0; extra == "test"
"""

mark_hashes_different = pytest.mark.xfail(
    sys.platform.startswith("win32") or sys.platform.startswith("cygwin"),
    reason="hashes differ on Windows",
)


def test_pep517_sdist(tmp_path, monkeypatch):

    dist = tmp_path.resolve() / "dist"
    monkeypatch.chdir(HELLO_PEP518)
    if Path("dist").is_dir():
        shutil.rmtree("dist")
    out = build_sdist(str(dist))

    (sdist,) = dist.iterdir()
    assert "cmake-example-0.0.1.tar.gz" == sdist.name
    assert sdist == dist / out

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
        assert pkg_info_contents == METADATA


@mark_hashes_different
def test_pep517_sdist_hash(tmp_path, monkeypatch):
    dist = tmp_path.resolve() / "dist"
    monkeypatch.chdir(HELLO_PEP518)
    if Path("dist").is_dir():
        shutil.rmtree("dist")
    out = build_sdist(str(dist))
    sdist = dist / out
    hash = hashlib.sha256(sdist.read_bytes()).hexdigest()
    if sys.version_info < (3, 9):
        assert (
            hash == "09b0593a80d0b0c086fddb99378e6dc75ba50e041076cd4a9a7afe4053407362"
        )
    else:
        assert (
            hash == "03455cc6996c1d0d4977bedb611180cf561ade9d70d7b5d1216a40405adf7b47"
        )


def test_pep517_sdist_time_hash(tmp_path, monkeypatch):
    dist = tmp_path.resolve() / "dist"
    monkeypatch.chdir(HELLO_PEP518)
    if Path("dist").is_dir():
        shutil.rmtree("dist")

    out = build_sdist(str(dist))
    sdist = dist / out
    hash1 = hashlib.sha256(sdist.read_bytes()).hexdigest()

    time.sleep(2)
    Path("src/main.cpp").touch()

    if Path("dist").is_dir():
        shutil.rmtree("dist")

    out = build_sdist(str(dist))
    sdist = dist / out

    hash2 = hashlib.sha256(sdist.read_bytes()).hexdigest()

    assert hash1 == hash2


def test_pep517_sdist_time_hash_nonreproducable(tmp_path, monkeypatch):
    dist = tmp_path.resolve() / "dist"
    monkeypatch.chdir(HELLO_PEP518)
    if Path("dist").is_dir():
        shutil.rmtree("dist")

    out = build_sdist(str(dist), {"sdist.reproducible": "false"})
    sdist = dist / out
    hash1 = hashlib.sha256(sdist.read_bytes()).hexdigest()

    time.sleep(2)

    if Path("dist").is_dir():
        shutil.rmtree("dist")

    out = build_sdist(str(dist))
    sdist = dist / out

    hash2 = hashlib.sha256(sdist.read_bytes()).hexdigest()

    assert hash1 != hash2


@mark_hashes_different
def test_pep517_sdist_time_hash_set_epoch(tmp_path, monkeypatch):
    dist = tmp_path.resolve() / "dist"
    monkeypatch.chdir(HELLO_PEP518)
    monkeypatch.setenv("SOURCE_DATE_EPOCH", "12345")
    if Path("dist").is_dir():
        shutil.rmtree("dist")

    out = build_sdist(str(dist), {"sdist.reproducible": "true"})
    sdist = dist / out
    hash = hashlib.sha256(sdist.read_bytes()).hexdigest()
    if sys.version_info < (3, 9):
        assert (
            hash == "7656ce7df4c1d6bbd098f046f75bb610104260542de5eeaf40993bb2976bf34e"
        )
    else:
        assert (
            hash == "a39a0eecb02f7b583ab3008c0c64c55eaef9d0bb5e712b6cb8d469598771ddfb"
        )


@pytest.mark.compile
@pytest.mark.configure
def test_pep517_wheel(tmp_path, monkeypatch, virtualenv):
    dist = tmp_path / "dist"
    dist.mkdir()
    monkeypatch.chdir(HELLO_PEP518)
    if Path("dist").is_dir():
        shutil.rmtree("dist")
    out = build_wheel(str(dist))
    (wheel,) = dist.glob("cmake_example-0.0.1-*.whl")
    assert wheel == dist / out

    if sys.version_info >= (3, 8):
        with wheel.open("rb") as f:
            p = zipfile.Path(f)
            file_names = [p.name for p in p.iterdir()]
            metadata = p.joinpath("cmake_example-0.0.1.dist-info/METADATA").read_text()
            entry_points = p.joinpath(
                "cmake_example-0.0.1.dist-info/entrypoints.txt"
            ).read_text()

        assert len(file_names) == 2
        assert "cmake_example-0.0.1.dist-info" in file_names
        file_names.remove("cmake_example-0.0.1.dist-info")
        (so_file,) = file_names

        assert so_file.startswith("cmake_example")
        print("SOFILE:", so_file)

        print(entry_points == ENTRYPOINTS)
        assert 'Requires-Dist: pytest>=6.0; extra == "test"' in metadata
        assert "Metadata-Version: 2.1" in metadata
        assert "Name: cmake-example" in metadata
        assert "Version: 0.0.1" in metadata
        assert "Requires-Python: >=3.7" in metadata
        assert "Provides-Extra: test" in metadata

    virtualenv.run(f"python -m pip install {wheel}")

    version = virtualenv.run(
        'python -c "import cmake_example; print(cmake_example.__version__)"',
        capture=True,
    )
    assert version.strip() == "0.0.1"

    add = virtualenv.run(
        'python -c "import cmake_example; print(cmake_example.add(1, 2))"',
        capture=True,
    )
    assert add.strip() == "3"


@pytest.mark.skip(reason="Doesn't work yet")
@pytest.mark.compile
@pytest.mark.configure
def test_pep517_wheel_time_hash(tmp_path, monkeypatch):
    dist = tmp_path / "dist"
    dist.mkdir()
    monkeypatch.chdir(HELLO_PEP518)
    monkeypatch.setenv("SOURCE_DATE_EPOCH", "12345")
    if Path("dist").is_dir():
        shutil.rmtree("dist")
    out = build_wheel(str(dist))
    wheel = dist / out
    hash1 = hashlib.sha256(wheel.read_bytes()).hexdigest()

    time.sleep(2)
    Path("src/main.cpp").touch()

    if Path("dist").is_dir():
        shutil.rmtree("dist")

    out = build_wheel(str(dist))
    wheel = dist / out

    hash2 = hashlib.sha256(wheel.read_bytes()).hexdigest()

    assert hash1 == hash2
