import sys
import sysconfig
import tarfile
import zipfile
from pathlib import Path

import download_wheels
import pytest

pytest.importorskip("hatchling")
from hatchling.builders.wheel import WheelBuilder


def set_hatchling_editable_mode(mode: str) -> None:
    pyproject = Path("pyproject.toml")
    pyproject.write_text(
        f'{pyproject.read_text(encoding="utf-8").rstrip()}\neditable.mode = "{mode}"\n',
        encoding="utf-8",
    )


@pytest.mark.network
@pytest.mark.integration
@pytest.mark.parametrize("package", ["hatchling"], indirect=True)
@pytest.mark.usefixtures("package")
def test_hatchling_sdist(isolated, tmp_path: Path) -> None:
    dist = tmp_path / "dist"
    isolated.install("build[virtualenv]")
    isolated.module("build", "--sdist", f"--outdir={dist}")
    (sdist,) = dist.iterdir()
    sdist = sdist.resolve()  # Windows mingw64 and UCRT now requires this
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
@pytest.mark.parametrize("package", ["hatchling"], indirect=True)
@pytest.mark.usefixtures("package")
@pytest.mark.parametrize(
    "build_args", [(), ("--wheel",)], ids=["sdist_to_wheel", "wheel_directly"]
)
def test_hatchling_wheel(isolated, build_args, tmp_path: Path) -> None:
    dist = tmp_path / "dist"
    isolated.install(
        "build[virtualenv]", "scikit-build-core", "hatchling", *download_wheels.EXTRA
    )
    isolated.module("build", "--no-isolation", f"--outdir={dist}", *build_args)
    ext_suffix = sysconfig.get_config_var("EXT_SUFFIX")

    (wheel,) = dist.glob("*.whl")
    wheel = wheel.resolve()  # Windows mingw64 and UCRT now requires this
    with zipfile.ZipFile(wheel) as f:
        file_names = set(f.namelist())
        wheel_metadata = f.read("hatchling_example-0.1.0.dist-info/WHEEL").decode(
            "utf-8"
        )
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
    assert "Root-Is-Purelib: false" in wheel_metadata


@pytest.mark.compile
@pytest.mark.configure
@pytest.mark.parametrize("package", ["hatchling"], indirect=True)
@pytest.mark.parametrize("editable_mode", ["redirect", "inplace"])
@pytest.mark.xfail(
    sys.platform.startswith("cygwin"),
    reason="Cygwin fails editable pybind11 link",
    strict=False,
)
@pytest.mark.usefixtures("package")
def test_hatchling_editable_wheel(editable_mode: str, tmp_path: Path) -> None:
    set_hatchling_editable_mode(editable_mode)
    dist = tmp_path / "dist"
    (wheel_str,) = WheelBuilder(str(Path.cwd())).build(
        directory=str(dist), versions=["editable"]
    )
    ext_suffix = sysconfig.get_config_var("EXT_SUFFIX")

    wheel = Path(wheel_str).resolve()
    with zipfile.ZipFile(wheel) as f:
        file_names = set(f.namelist())
        pth_contents = f.read("_hatchling_example_editable.pth").decode("utf-8")
        wheel_metadata = f.read("hatchling_example-0.1.0.dist-info/WHEEL").decode(
            "utf-8"
        )

    assert "hatchling_example-0.1.0.dist-info/METADATA" in file_names
    assert "_hatchling_example_editable.pth" in file_names
    assert "Root-Is-Purelib: false" in wheel_metadata
    if editable_mode == "redirect":
        assert "_hatchling_example_editable.py" in file_names
        assert f"hatchling_example/_core{ext_suffix}" in file_names
        assert pth_contents.splitlines()[0] == "import _hatchling_example_editable"
    else:
        assert "_hatchling_example_editable.py" not in file_names
        assert f"hatchling_example/_core{ext_suffix}" not in file_names
        assert Path(pth_contents.strip()).resolve().samefile(Path("src").resolve())


@pytest.mark.compile
@pytest.mark.configure
@pytest.mark.integration
@pytest.mark.parametrize("package", ["hatchling"], indirect=True)
@pytest.mark.parametrize("editable_mode", ["redirect", "inplace"])
@pytest.mark.xfail(
    sys.platform.startswith("cygwin"),
    reason="Cygwin fails editable pybind11 link",
    strict=False,
)
@pytest.mark.usefixtures("package")
def test_hatchling_editable_install(isolated, editable_mode: str) -> None:
    set_hatchling_editable_mode(editable_mode)
    isolated.install(
        "-v",
        "scikit-build-core",
        "hatchling",
        "pybind11",
        *download_wheels.EXTRA,
        isolated=False,
    )
    isolated.install("-v", "-e", ".", isolated=False)

    assert (
        isolated.execute("import hatchling_example; print(hatchling_example.add(1, 2))")
        == "3"
    )
    assert (
        isolated.execute(
            "import hatchling_example; print(hatchling_example.subtract(5, 2))"
        )
        == "3"
    )
    location = isolated.execute(
        "import hatchling_example; print(hatchling_example.__file__)"
    )
    assert (
        Path("src/hatchling_example/__init__.py")
        .resolve()
        .samefile(Path(location).resolve())
    )

    ext_suffix = sysconfig.get_config_var("EXT_SUFFIX")
    ext_location = isolated.execute(
        "import hatchling_example._core; print(hatchling_example._core.__file__)"
    )
    if editable_mode == "redirect":
        expected = isolated.platlib / "hatchling_example" / f"_core{ext_suffix}"
    else:
        expected = Path("src/hatchling_example") / f"_core{ext_suffix}"
    assert expected.resolve().samefile(Path(ext_location).resolve())
