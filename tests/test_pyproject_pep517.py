import hashlib
import shutil
import sys
import tarfile
import time
import zipfile
from pathlib import Path

import build.util
import pytest

from scikit_build_core.build import _file_processor, build_sdist, build_wheel

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
    strict=False,
)


def test_pep517_sdist(tmp_path, monkeypatch):
    dist = tmp_path.resolve() / "dist"
    monkeypatch.chdir(HELLO_PEP518)
    if Path("dist").is_dir():
        shutil.rmtree("dist")
    out = build_sdist(str(dist))

    (sdist,) = dist.iterdir()
    assert sdist.name == "cmake-example-0.0.1.tar.gz"
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
            hash == "3b4af3fbe3d4505415bb1e55bb2e49902f4633d371ae7288007d90eb1488bc4d"
        )
    else:
        assert (
            hash == "d373b8458ee37b176cfd03f0f3199b30fdb034bca465b2826392a6c3af85ca4c"
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
@pytest.mark.parametrize("reverse_order", [False, True])
def test_pep517_sdist_time_hash_set_epoch(tmp_path, monkeypatch, reverse_order):
    dist = tmp_path.resolve() / "dist"
    monkeypatch.chdir(HELLO_PEP518)
    monkeypatch.setenv("SOURCE_DATE_EPOCH", "12345")
    if Path("dist").is_dir():
        shutil.rmtree("dist")

    _each_unignored_file = _file_processor.each_unignored_file

    def each_unignored_file_ordered(*args, **kwargs):
        return sorted(_each_unignored_file(*args, **kwargs), reverse=reverse_order)

    monkeypatch.setattr(
        _file_processor, "each_unignored_file", each_unignored_file_ordered
    )

    out = build_sdist(str(dist), {"sdist.reproducible": "true"})
    sdist = dist / out
    hash = hashlib.sha256(sdist.read_bytes()).hexdigest()
    if sys.version_info < (3, 9):
        assert (
            hash == "99d54d3090f932f00b77f01d12d422aacb674a6a9afd6af24f7afaaab7c3082b"
        )
    else:
        assert (
            hash == "359e38eb01415440cc8f7d9ee09612d625b8906ca09cd08c9d56f3eb972b0110"
        )


@pytest.mark.compile()
@pytest.mark.configure()
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
                "cmake_example-0.0.1.dist-info/entry_points.txt"
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

    virtualenv.install(wheel)

    version = virtualenv.execute(
        "import cmake_example; print(cmake_example.__version__)",
    )
    assert version.strip() == "0.0.1"

    add = virtualenv.execute(
        "import cmake_example; print(cmake_example.add(1, 2))",
    )
    assert add.strip() == "3"


@pytest.mark.skip(reason="Doesn't work yet")
@pytest.mark.compile()
@pytest.mark.configure()
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


def test_prepare_metdata_for_build_wheel():
    metadata = build.util.project_wheel_metadata(HELLO_PEP518, isolated=False)
    answer = {
        "Metadata-Version": "2.1",
        "Name": "cmake-example",
        "Version": "0.0.1",
        "Requires-Python": ">=3.7",
        "Provides-Extra": "test",
        "Requires-Dist": 'pytest>=6.0; extra == "test"',
    }

    for k, b in answer.items():
        assert metadata[k] == b

    assert len(metadata) == len(answer)
