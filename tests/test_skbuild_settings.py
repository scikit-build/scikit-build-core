from __future__ import annotations

import textwrap

from scikit_build_core.settings.skbuild_settings import read_settings


def test_skbuild_settings_default(tmp_path):
    pyproject_toml = tmp_path / "pyproject.toml"
    pyproject_toml.write_text("", encoding="utf-8")

    config_settings: dict[str, list[str] | str] = {}

    settings = read_settings(pyproject_toml, config_settings)

    assert settings.cmake.minimum_version == "3.15"
    assert settings.ninja.minimum_version == "1.5"


def test_skbuild_settings_envvar(tmp_path, monkeypatch):
    monkeypatch.setenv("SKBUILD_CMAKE_MINIMUM_VERSION", "3.16")
    monkeypatch.setenv("SKBUILD_NINJA_MINIMUM_VERSION", "1.1")

    pyproject_toml = tmp_path / "pyproject.toml"
    pyproject_toml.write_text("", encoding="utf-8")

    config_settings: dict[str, list[str] | str] = {}

    settings = read_settings(pyproject_toml, config_settings)

    assert settings.cmake.minimum_version == "3.16"
    assert settings.ninja.minimum_version == "1.1"


def test_skbuild_settings_config_settings(tmp_path):
    pyproject_toml = tmp_path / "pyproject.toml"
    pyproject_toml.write_text("", encoding="utf-8")

    config_settings = {
        "scikit-build.cmake.minimum-version": "3.17",
        "scikit-build.ninja.minimum-version": "1.2",
    }

    settings = read_settings(pyproject_toml, config_settings)

    assert settings.cmake.minimum_version == "3.17"
    assert settings.ninja.minimum_version == "1.2"


def test_skbuild_settings_pyproject_toml(tmp_path):
    pyproject_toml = tmp_path / "pyproject.toml"
    pyproject_toml.write_text(
        textwrap.dedent(
            """\
            [tool.scikit-build]
            cmake.minimum-version = "3.18"
            ninja.minimum-version = "1.3"
            """
        ),
        encoding="utf-8",
    )

    config_settings: dict[str, list[str] | str] = {}

    settings = read_settings(pyproject_toml, config_settings)

    assert settings.cmake.minimum_version == "3.18"
    assert settings.ninja.minimum_version == "1.3"
