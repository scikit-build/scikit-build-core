import shutil
import sys
import zipfile
from pathlib import Path
from unittest import mock

import git
import pyproject_metadata
import pytest

from scikit_build_core._compat import importlib
from scikit_build_core.build import build_wheel
from scikit_build_core.settings.metadata import get_standard_metadata
from scikit_build_core.settings.skbuild_read_settings import SettingsReader

DIR = Path(__file__).parent.resolve()
DYNAMIC = DIR / "packages/dynamic_metadata"


@pytest.fixture()
def mock_entry_points():
    mock_version = mock.Mock()
    mock_version.load.return_value = lambda _: "0.0.2"
    mock_version.name = "test_version"
    mock_version.group = "skbuild"
    mock_version.matches.side_effect = AttributeError()

    mock_readme = mock.Mock()
    mock_readme.load.return_value = lambda _: {
        "content-type": "text/x-rst",
        "text": "Some text",
    }
    mock_readme.name = "test_readme"
    mock_readme.group = "skbuild"
    mock_readme.matches.side_effect = AttributeError()

    mock_license = mock.Mock()
    mock_license.load.return_value = lambda _: {"text": "MIT License"}
    mock_license.name = "test_license"
    mock_license.group = "skbuild"
    mock_license.matches.side_effect = AttributeError()

    def mock_ep(**_):
        result: importlib.metadata.EntryPoints = importlib.metadata.EntryPoints(
            (mock_version, mock_readme, mock_license)
        )
        return result

    with mock.patch(
        "scikit_build_core.settings.metadata.importlib.metadata.entry_points", mock_ep
    ) as mocked:
        yield mocked


@pytest.mark.usefixtures("mock_entry_points")
def test_dynamic_metadata(monkeypatch):
    monkeypatch.chdir(DYNAMIC)

    settings_reader = SettingsReader(Path("pyproject.toml"), {})
    settings = settings_reader.settings

    settings_reader.validate_may_exit()

    metadata = get_standard_metadata(Path("pyproject.toml"), settings)

    assert str(metadata.version) == "0.0.2"
    assert metadata.license == pyproject_metadata.License("MIT License", None)
    assert metadata.readme == pyproject_metadata.Readme("Some text", None, "text/x-rst")


def test_fancy_metadata(tmp_path, monkeypatch):
    build_dir = tmp_path / "build"

    shutil.copytree(DYNAMIC, build_dir)
    monkeypatch.chdir(build_dir)

    repo = git.repo.base.Repo.init(build_dir, initial_branch="main")
    repo.config_writer().set_value("user", "name", "bot").release()
    repo.config_writer().set_value("user", "email", "bot@scikit-build.net").release()
    repo.index.add(["pyproject.toml"])
    repo.index.commit("first commit")
    repo.create_tag("v0.1.0", message="initial commit")

    settings_reader = SettingsReader(Path("fancy_project.toml"), {})
    settings = settings_reader.settings

    settings_reader.validate_may_exit()

    metadata = get_standard_metadata(Path("fancy_project.toml"), settings)

    assert str(metadata.version) == "0.1.0"
    assert metadata.readme == pyproject_metadata.Readme(
        "Fragment #1Fragment #2", None, "text/x-rst"
    )


def test_faulty_metadata(monkeypatch):
    monkeypatch.chdir(DYNAMIC)
    settings_reader = SettingsReader(Path("faulty_project.toml"), {})
    settings = settings_reader.settings

    settings_reader.validate_may_exit()

    with pytest.raises(KeyError):
        get_standard_metadata(Path("faulty_project.toml"), settings)


def test_warn_metadata(monkeypatch):
    monkeypatch.chdir(DYNAMIC)
    settings_reader = SettingsReader(Path("warn_project.toml"), {})
    settings = settings_reader.settings

    settings_reader.validate_may_exit()

    with pytest.warns():
        get_standard_metadata(Path("warn_project.toml"), settings)


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
