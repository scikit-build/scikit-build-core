from __future__ import annotations

import sys
import sysconfig
import tarfile
import zipfile
from pathlib import Path

import download_wheels
import pytest

pytest.importorskip("hatchling")
from hatchling.builders.wheel import WheelBuilder

from scikit_build_core.hatch.plugin import ScikitBuildHook
from scikit_build_core.settings.skbuild_read_settings import (
    SettingsReader,
)


def _validate_settings(pyproject: dict[str, object]) -> None:
    reader = SettingsReader(pyproject, {}, state="sdist")
    # _validate only uses the settings_reader argument, not self.
    ScikitBuildHook._validate(None, reader)  # type: ignore[arg-type]


def test_hatchling_sdist_cmake_error_message() -> None:
    pyproject = {
        "project": {"name": "x", "version": "0.1.0"},
        "tool": {"scikit-build": {"sdist": {"cmake": True}}},
    }
    with pytest.raises(ValueError, match="Not currently supported for SDist builds"):
        _validate_settings(pyproject)


def test_hatchling_force_include_rejected() -> None:
    pyproject = {
        "project": {"name": "x", "version": "0.1.0"},
        "tool": {"scikit-build": {"force-include": {"a.txt": "pkg/a.txt"}}},
    }
    with pytest.raises(ValueError, match="Force-include is not supported"):
        _validate_settings(pyproject)


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
            "hatchling_example-0.1.0/cpp/example.c",
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
        f"hatchling_example/_core{ext_suffix}",
    }
    assert "Root-Is-Purelib: false" in wheel_metadata

    # The built wheel must be importable (regression test for the doubled
    # install_dir prefix that produced an unimportable layout).
    isolated.install(str(wheel), isolated=False)
    assert (
        isolated.execute("import hatchling_example; print(hatchling_example.add(1, 2))")
        == "3"
    )


@pytest.mark.compile
@pytest.mark.configure
@pytest.mark.parametrize("package", ["hatchling"], indirect=True)
@pytest.mark.parametrize("editable_mode", ["redirect", "inplace"])
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
        # The hatchling example always discovers a package (src/), so a .pth is
        # always emitted (in pep829 redirect mode it carries only the paths).
        pth_lines = [
            ln
            for ln in f.read("_editable_skbc_hatchling_example.pth")
            .decode("utf-8")
            .splitlines()
            if ln
        ]
        start_contents = (
            f.read("_editable_skbc_hatchling_example.start")
            if "_editable_skbc_hatchling_example.start" in file_names
            else None
        )
        wheel_metadata = f.read("hatchling_example-0.1.0.dist-info/WHEEL").decode(
            "utf-8"
        )

    # PEP 829: redirect mode moves the import line into a .start file on 3.15+
    pep829 = sys.version_info >= (3, 15)

    assert "hatchling_example-0.1.0.dist-info/METADATA" in file_names
    assert "_editable_skbc_hatchling_example.pth" in file_names
    assert "Root-Is-Purelib: false" in wheel_metadata
    if editable_mode == "redirect":
        assert "_editable_skbc_hatchling_example.py" in file_names
        assert f"hatchling_example/_core{ext_suffix}" in file_names
        if pep829:
            assert (
                start_contents
                == "_editable_skbc_hatchling_example:entrypoint".encode("utf-8-sig")
            )
            # The .pth keeps only the path entries, no import line
            assert Path(pth_lines[0]).resolve().samefile(Path("src").resolve())
        else:
            assert start_contents is None
            assert pth_lines[0] == "import _editable_skbc_hatchling_example"
    else:
        assert "_editable_skbc_hatchling_example.py" not in file_names
        assert start_contents is None
        assert f"hatchling_example/_core{ext_suffix}" not in file_names
        assert Path(pth_lines[0]).resolve().samefile(Path("src").resolve())


@pytest.mark.compile
@pytest.mark.configure
@pytest.mark.integration
@pytest.mark.parametrize("package", ["hatchling"], indirect=True)
@pytest.mark.parametrize("editable_mode", ["redirect", "inplace"])
@pytest.mark.usefixtures("package")
def test_hatchling_editable_install(isolated, editable_mode: str) -> None:
    set_hatchling_editable_mode(editable_mode)
    isolated.install(
        "scikit-build-core",
        "hatchling",
        *download_wheels.EXTRA,
    )
    isolated.install("-v", "-e", ".", isolated=False, installer="pip")

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
