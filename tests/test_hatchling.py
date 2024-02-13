import tarfile
from pathlib import Path

import pytest


@pytest.mark.network()
@pytest.mark.integration()
@pytest.mark.usefixtures("package_hatchling")
def test_hatchling_sdist(isolated) -> None:
    isolated.install("build[virtualenv]")
    isolated.module("build", "--sdist")
    (sdist,) = Path("dist").iterdir()
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


@pytest.mark.network()
@pytest.mark.compile()
@pytest.mark.configure()
@pytest.mark.integration()
@pytest.mark.usefixtures("package_hatchling")
@pytest.mark.parametrize(
    "build_args", [(), ("--wheel",)], ids=["sdist_to_wheel", "wheel_directly"]
)
def test_hatchling_wheel(isolated, build_args) -> None:
    isolated.install("build[virtualenv]", "scikit-build-core", "hatchling", "pybind11")
    isolated.module("build", "--no-isolation", *build_args)
