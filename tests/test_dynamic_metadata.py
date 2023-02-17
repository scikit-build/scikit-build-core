from __future__ import annotations

import shutil
import sys
import zipfile
from pathlib import Path
from typing import Any
from unittest import mock

import git
import pyproject_metadata
import pytest

from scikit_build_core._compat import importlib, tomllib
from scikit_build_core.build import build_wheel
from scikit_build_core.settings.metadata import get_standard_metadata
from scikit_build_core.settings.skbuild_read_settings import SettingsReader

DIR = Path(__file__).parent.resolve()
DYNAMIC = DIR / "packages/dynamic_metadata"


# these are mock plugins returning known results
# it turns out to be easier to create EntryPoint objects pointing to real
# functions than to mock them.
def ep_version(_pyproject_dict: dict[str, Any]) -> str:
    return "0.0.2"


def ep_readme(_pyproject_dict: dict[str, Any]) -> dict[str, str]:
    return {
        "content-type": "text/x-rst",
        "text": "Some text",
    }


def ep_license(_pyproject_dict: dict[str, Any]) -> dict[str, str]:
    return {"text": "MIT License"}


@pytest.fixture()
def mock_entry_points():
    mocked = importlib.metadata.EntryPoints(
        (
            importlib.metadata.EntryPoint(  # type: ignore[no-untyped-call]
                "test_version", f"{__name__}:ep_version", "scikit_build.metadata"
            ),
            importlib.metadata.EntryPoint(  # type: ignore[no-untyped-call]
                "test_license", f"{__name__}:ep_license", "scikit_build.metadata"
            ),
            importlib.metadata.EntryPoint(  # type: ignore[no-untyped-call]
                "test_readme", f"{__name__}:ep_readme", "scikit_build.metadata"
            ),
        )
    )

    with mock.patch(
        "scikit_build_core.settings.metadata.importlib.metadata.entry_points"
    ) as mocked_eps:
        mocked_eps.return_value = mocked
        yield mocked


@pytest.mark.usefixtures("mock_entry_points")
def test_dynamic_metadata(monkeypatch):
    monkeypatch.chdir(DYNAMIC)

    with Path("pyproject.toml").open("rb") as ft:
        pyproject = tomllib.load(ft)
    settings_reader = SettingsReader(pyproject, {})
    settings = settings_reader.settings

    settings_reader.validate_may_exit()

    metadata = get_standard_metadata(pyproject, settings)

    assert str(metadata.version) == "0.0.2"
    assert metadata.license == pyproject_metadata.License("MIT License", None)
    assert metadata.readme == pyproject_metadata.Readme("Some text", None, "text/x-rst")


def test_plugin_metadata(tmp_path, monkeypatch):
    reason_msg = (
        "install hatch-fancy-pypi-readme and setuptools-scm to test the "
        "dynamic metadata plugins"
    )
    pytest.importorskip("hatch_fancy_pypi_readme", reason=reason_msg)
    pytest.importorskip("setuptools_scm", reason=reason_msg)
    build_dir = tmp_path / "build"
    build_dir.mkdir()

    shutil.copy(DYNAMIC / "plugin_project.toml", build_dir / "pyproject.toml")
    monkeypatch.chdir(build_dir)

    repo = git.repo.base.Repo.init(build_dir, initial_branch="main")
    repo.config_writer().set_value("user", "name", "bot").release()
    repo.config_writer().set_value("user", "email", "bot@scikit-build.net").release()
    repo.index.add(["pyproject.toml"])
    repo.index.commit("first commit")
    repo.create_tag("v0.1.0", message="initial commit")

    with Path("pyproject.toml").open("rb") as ft:
        pyproject = tomllib.load(ft)
    settings_reader = SettingsReader(pyproject, {})
    settings = settings_reader.settings

    settings_reader.validate_may_exit()

    metadata = get_standard_metadata(pyproject, settings)

    assert str(metadata.version) == "0.1.0"
    assert metadata.readme == pyproject_metadata.Readme(
        "Fragment #1Fragment #2", None, "text/x-rst"
    )


def test_faulty_metadata(monkeypatch):
    monkeypatch.chdir(DYNAMIC)

    with Path("faulty_project.toml").open("rb") as ft:
        pyproject = tomllib.load(ft)
    settings_reader = SettingsReader(pyproject, {})
    settings = settings_reader.settings

    settings_reader.validate_may_exit()

    with pytest.raises(KeyError):
        get_standard_metadata(pyproject, settings)


def test_warn_metadata(monkeypatch):
    monkeypatch.chdir(DYNAMIC)
    with Path("warn_project.toml").open("rb") as ft:
        pyproject = tomllib.load(ft)
    settings_reader = SettingsReader(pyproject, {})
    settings = settings_reader.settings

    settings_reader.validate_may_exit()

    with pytest.warns():
        get_standard_metadata(pyproject, settings)


@pytest.mark.compile()
@pytest.mark.configure()
@pytest.mark.usefixtures("mock_entry_points")
def test_pep517_wheel(tmp_path, monkeypatch, virtualenv):
    dist = tmp_path.resolve() / "dist"
    monkeypatch.chdir(DYNAMIC)
    if Path("dist").is_dir():
        shutil.rmtree("dist")

    out = build_wheel(str(dist))
    (wheel,) = dist.glob("dynamic-0.0.2-*.whl")
    assert wheel == dist / out

    virtualenv.install(wheel)
    license = virtualenv.execute(
        "from importlib.metadata import metadata; print(metadata('dynamic')['License'])"
    )
    assert license == "MIT License"

    if sys.version_info >= (3, 8):
        with wheel.open("rb") as f:
            p = zipfile.Path(f)
            file_names = {x.name for x in p.iterdir()}
            dynamic_pkg = {x.name for x in p.joinpath("dynamic").iterdir()}

        filtered_pkg = {x for x in dynamic_pkg if not x.startswith("_module")}

        assert len(filtered_pkg) == len(dynamic_pkg) - 1
        assert {"dynamic-0.0.2.dist-info", "dynamic"} == file_names
        assert {
            "__init__.py",
        } == filtered_pkg

    version = virtualenv.execute("from dynamic import square; print(square(2))")
    assert version == "4.0"
