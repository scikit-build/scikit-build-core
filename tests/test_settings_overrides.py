from pathlib import Path
from textwrap import dedent

import pytest

from scikit_build_core.settings.skbuild_read_settings import SettingsReader


@pytest.mark.parametrize("python_version", ["3.9", "3.10"])
def test_skbuild_overrides_pyver(
    python_version: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    monkeypatch.setattr("sys.version_info", (*map(int, python_version.split(".")), 0))
    pyproject_toml = tmp_path / "pyproject.toml"
    pyproject_toml.write_text(
        dedent(
            """\
        [[tool.scikit-build.overrides]]
        select = {python-version = ">=3.10"}
        cmake.args = ["-DFOO=BAR"]
        experimental = true
        cmake.define.SPAM = "EGGS"
        sdist.cmake = true
    """
        ),
        encoding="utf-8",
    )

    settings_reader = SettingsReader.from_file(pyproject_toml, {})
    settings = settings_reader.settings

    if python_version == "3.10":
        assert settings.cmake.args == ["-DFOO=BAR"]
        assert settings.cmake.define == {"SPAM": "EGGS"}
        assert settings.experimental
        assert settings.sdist.cmake
    else:
        assert not settings.cmake.args
        assert not settings.cmake.define
        assert not settings.experimental
        assert not settings.sdist.cmake


@pytest.mark.parametrize("implementation_name", ["cpython", "pypy"])
@pytest.mark.parametrize("platform_system", ["darwin", "linux"])
def test_skbuild_overrides_dual(
    implementation_name: str,
    platform_system: str,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.setattr(
        "sys.implementation", type("Mock", (), {"name": implementation_name})
    )
    monkeypatch.setattr("sys.platform", platform_system)

    pyproject_toml = tmp_path / "pyproject.toml"
    pyproject_toml.write_text(
        dedent(
            """\
        [[tool.scikit-build.overrides]]
        select = {implementation-name = "pypy", platform-system = "darwin"}
        editable.verbose = false
        install.components = ["headers"]
    """
        ),
        encoding="utf-8",
    )

    settings_reader = SettingsReader.from_file(pyproject_toml, {})
    settings = settings_reader.settings

    if implementation_name == "pypy" and platform_system == "darwin":
        assert not settings.editable.verbose
        assert settings.install.components == ["headers"]
    else:
        assert settings.editable.verbose
        assert not settings.install.components
