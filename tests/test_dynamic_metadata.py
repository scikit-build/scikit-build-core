from __future__ import annotations

import importlib
import shutil
import subprocess
import sys
import types
import zipfile
from pathlib import Path
from typing import Any

import pytest
from packaging.version import Version

from scikit_build_core._compat import tomllib
from scikit_build_core._vendor import pyproject_metadata
from scikit_build_core.build import build_wheel
from scikit_build_core.build.metadata import get_standard_metadata
from scikit_build_core.builder.get_requires import GetRequires
from scikit_build_core.metadata import regex
from scikit_build_core.settings.skbuild_read_settings import SettingsReader

from pathutils import contained


# these are mock plugins returning known results
# it turns out to be easier to create EntryPoint objects pointing to real
# functions than to mock them.
def ep_version(
    field: str,
    _settings: dict[str, object] | None = None,
) -> str:
    assert field == "version"
    return "0.0.2"


def ep_readme(
    field: str,
    _settings: dict[str, object] | None = None,
) -> str | dict[str, str | None]:
    assert field == "readme"
    return {
        "content-type": "text/x-rst",
        "text": "Some text",
    }


def ep_license(
    field: str,
    _settings: dict[str, object] | None = None,
) -> dict[str, str | None]:
    assert field == "license"
    return {"text": "MIT License"}


def ep_dual(
    _field: str,
    _settings: dict[str, object] | None = None,
) -> str | dict[str, str | None]:
    # Fields intentionally not checked to verify backend error thrown
    if _field == "version":
        return "0.3"
    if _field == "license":
        return {"text": "BSD License"}
    msg = f"Invalid field {_field}"
    raise KeyError(msg)


original_loader = importlib.import_module


def special_loader(name: str, *args: Any, **kwargs: Any) -> Any:
    if name == "test_version":
        test_version = types.ModuleType("test_version")
        test_version.dynamic_metadata = ep_version  # type: ignore[attr-defined]
        return test_version
    if name == "test_readme":
        test_readme = types.ModuleType("test_readme")
        test_readme.dynamic_metadata = ep_readme  # type: ignore[attr-defined]
        return test_readme
    if name == "test_license":
        test_license = types.ModuleType("test_license")
        test_license.dynamic_metadata = ep_license  # type: ignore[attr-defined]
        return test_license
    if name == "test_dual":
        test_dual = types.ModuleType("test_dual")
        test_dual.dynamic_metadata = ep_dual  # type: ignore[attr-defined]
        return test_dual

    return original_loader(name, *args, **kwargs)


@pytest.fixture()
def mock_entry_points(monkeypatch):
    monkeypatch.setattr(importlib, "import_module", special_loader)


@pytest.mark.usefixtures("mock_entry_points", "package_dynamic_metadata")
def test_dynamic_metadata():
    with Path("pyproject.toml").open("rb") as ft:
        pyproject = tomllib.load(ft)
    settings_reader = SettingsReader(pyproject, {}, state="metadata_wheel")
    settings = settings_reader.settings

    settings_reader.validate_may_exit()

    metadata = get_standard_metadata(pyproject, settings)

    assert str(metadata.version) == "0.0.2"
    assert metadata.license == pyproject_metadata.License("MIT License", None)
    assert metadata.readme == pyproject_metadata.Readme("Some text", None, "text/x-rst")


@pytest.mark.usefixtures("package_dynamic_metadata")
def test_plugin_metadata():
    reason_msg = (
        "install hatch-fancy-pypi-readme and setuptools-scm to test the "
        "dynamic metadata plugins"
    )
    pytest.importorskip("hatch_fancy_pypi_readme", reason=reason_msg)
    pytest.importorskip("setuptools_scm", reason=reason_msg)
    if shutil.which("git") is None:
        pytest.skip("git is not installed")

    shutil.copy("plugin_project.toml", "pyproject.toml")

    subprocess.run(["git", "init", "--initial-branch=main"], check=True)
    subprocess.run(["git", "config", "user.name", "bot"], check=True)
    subprocess.run(["git", "config", "user.email", "bot@scikit-build.org"], check=True)
    subprocess.run(["git", "add", "pyproject.toml"], check=True)
    subprocess.run(["git", "commit", "-m", "initial commit"], check=True)
    subprocess.run(["git", "tag", "v0.1.0", "-m", "initial commint"], check=True)

    with Path("pyproject.toml").open("rb") as ft:
        pyproject = tomllib.load(ft)
    settings_reader = SettingsReader(pyproject, {}, state="metadata_wheel")
    settings = settings_reader.settings

    settings_reader.validate_may_exit()

    metadata = get_standard_metadata(pyproject, settings)

    assert str(metadata.version) == "0.1.0"
    assert metadata.readme == pyproject_metadata.Readme(
        "Fragment #1Fragment #2", None, "text/x-rst"
    )

    assert set(GetRequires().dynamic_metadata()) == {
        "hatch-fancy-pypi-readme>=22.3",
        "setuptools-scm",
    }


@pytest.mark.usefixtures("package_dynamic_metadata")
def test_faulty_metadata():
    with Path("faulty_project.toml").open("rb") as ft:
        pyproject = tomllib.load(ft)
    settings_reader = SettingsReader(pyproject, {}, state="metadata_wheel")
    settings = settings_reader.settings

    settings_reader.validate_may_exit()

    with pytest.raises(KeyError):
        get_standard_metadata(pyproject, settings)


@pytest.mark.usefixtures("package_dynamic_metadata")
def test_local_plugin_metadata():
    with Path("local_pyproject.toml").open("rb") as ft:
        pyproject = tomllib.load(ft)
    settings_reader = SettingsReader(pyproject, {}, state="metadata_wheel")
    settings = settings_reader.settings

    settings_reader.validate_may_exit()

    metadata = get_standard_metadata(pyproject, settings)
    assert metadata.version == Version("3.2.1")


@pytest.mark.usefixtures("package_dynamic_metadata")
def test_warn_metadata():
    with Path("warn_project.toml").open("rb") as ft:
        pyproject = tomllib.load(ft)
    settings_reader = SettingsReader(pyproject, {}, state="metadata_wheel")
    settings = settings_reader.settings

    settings_reader.validate_may_exit()

    with pytest.raises(ModuleNotFoundError):
        get_standard_metadata(pyproject, settings)


@pytest.mark.usefixtures("package_dynamic_metadata")
def test_fail_experimental_metadata():
    with Path("warn_project.toml").open("rb") as ft:
        pyproject = tomllib.load(ft)
    settings_reader = SettingsReader(
        pyproject, {"experimental": "false"}, state="metadata_wheel"
    )

    with pytest.raises(SystemExit) as exc:
        settings_reader.validate_may_exit()
    (value,) = exc.value.args
    assert value == 7


@pytest.mark.usefixtures("mock_entry_points", "package_dynamic_metadata")
def test_dual_metadata():
    with Path("dual_project.toml").open("rb") as ft:
        pyproject = tomllib.load(ft)
    settings_reader = SettingsReader(pyproject, {}, state="metadata_wheel")
    settings = settings_reader.settings

    settings_reader.validate_may_exit()

    metadata = get_standard_metadata(pyproject, settings)
    assert str(metadata.version) == "0.3"
    assert metadata.license == pyproject_metadata.License("BSD License", None)

    with Path("faulty_dual_project.toml").open("rb") as ft:
        pyproject = tomllib.load(ft)
    settings_reader = SettingsReader(pyproject, {}, state="metadata_wheel")
    settings = settings_reader.settings

    settings_reader.validate_may_exit()

    with pytest.raises(KeyError):
        get_standard_metadata(pyproject, settings)


@pytest.mark.compile()
@pytest.mark.configure()
@pytest.mark.usefixtures("mock_entry_points", "package_dynamic_metadata")
def test_pep517_wheel(virtualenv):
    dist = Path("dist")
    out = build_wheel("dist")
    (wheel,) = dist.glob("dynamic-0.0.2-*.whl")
    assert wheel == dist / out

    virtualenv.install(wheel)
    if sys.version_info >= (3, 8):
        license = virtualenv.execute(
            "from importlib.metadata import metadata; print(metadata('dynamic')['License'])"
        )
        assert license == "MIT License"

    with zipfile.ZipFile(wheel) as zf:
        file_paths = {Path(n) for n in zf.namelist()}

    dynamic_pkg = {x.name for x in contained(file_paths, "dynamic")}
    filtered_pkg = {x for x in dynamic_pkg if not x.startswith("_module")}

    assert len(filtered_pkg) == len(dynamic_pkg) - 1
    assert {"dynamic-0.0.2.dist-info", "dynamic"} == {p.parts[0] for p in file_paths}
    assert {"__init__.py"} == filtered_pkg

    version = virtualenv.execute("from dynamic import square; print(square(2))")
    assert version == "4.0"


def test_regex(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    d = tmp_path / "test_regex"
    d.mkdir()
    monkeypatch.chdir(d)

    with Path("__init__.py").open("w") as f:
        f.write("__version__ = '0.1.0'")

    regex.dynamic_metadata("version", {"input": "__init__.py"})


def test_regex_errors() -> None:
    with pytest.raises(RuntimeError):
        regex.dynamic_metadata("version", {})
    with pytest.raises(RuntimeError, match="Only string fields supported"):
        regex.dynamic_metadata("author", {"input": "x", "regex": "x"})
