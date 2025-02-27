import sysconfig
import tarfile
import zipfile
from pathlib import Path

import pytest

pytest.importorskip("hatchling")


@pytest.mark.network
@pytest.mark.integration
@pytest.mark.usefixtures("package_hatchling")
def test_hatchling_sdist(isolated, tmp_path: Path) -> None:
    dist = tmp_path / "dist"
    isolated.install("build[virtualenv]")
    isolated.module("build", "--sdist", f"--outdir={dist}")
    (sdist,) = dist.iterdir()
    assert sdist.name == "hatchling_example-0.1.0.tar.gz"
    with tarfile.open(sdist) as f:
        file_names = set(f.getnames())
        assert file_names == {
            "hatchling_example-0.1.0/.gitignore",
            "hatchling_example-0.1.0/PKG-INFO",
            "hatchling_example-0.1.0/cpp/CMakeLists.txt",
            "hatchling_example-0.1.0/cpp/example.cpp",
            "hatchling_example-0.1.0/pyproject.toml",
            "hatchling_example-0.1.0/src/hatchling_example/__init__.py",
            "hatchling_example-0.1.0/src/hatchling_example/_core.pyi",
        }


@pytest.mark.network
@pytest.mark.compile
@pytest.mark.configure
@pytest.mark.integration
@pytest.mark.usefixtures("package_hatchling")
@pytest.mark.parametrize(
    "build_args", [(), ("--wheel",)], ids=["sdist_to_wheel", "wheel_directly"]
)
def test_hatchling_wheel(isolated, build_args, tmp_path: Path) -> None:
    dist = tmp_path / "dist"
    isolated.install("build[virtualenv]", "scikit-build-core", "hatchling", "pybind11")
    isolated.module("build", "--no-isolation", f"--outdir={dist}", *build_args)
    ext_suffix = sysconfig.get_config_var("EXT_SUFFIX")

    (wheel,) = dist.glob("*.whl")
    with zipfile.ZipFile(wheel) as f:
        file_names = set(f.namelist())
    assert file_names == {
        "hatchling_example-0.1.0.data/data/data_file.txt",
        "hatchling_example-0.1.0.data/scripts/myscript",
        "hatchling_example-0.1.0.dist-info/METADATA",
        "hatchling_example-0.1.0.dist-info/RECORD",
        "hatchling_example-0.1.0.dist-info/WHEEL",
        "hatchling_example-0.1.0.dist-info/extra_metadata/metadata_file.txt",
        "hatchling_example/__init__.py",
        "hatchling_example/_core.pyi",
        f"hatchling_example/hatchling_example/_core{ext_suffix}",
    }
