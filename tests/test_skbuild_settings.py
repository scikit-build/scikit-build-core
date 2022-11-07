from __future__ import annotations

import textwrap

from scikit_build_core.settings.skbuild_read_settings import read_settings


def test_skbuild_settings_default(tmp_path):
    pyproject_toml = tmp_path / "pyproject.toml"
    pyproject_toml.write_text("", encoding="utf-8")

    config_settings: dict[str, list[str] | str] = {}

    settings = read_settings(pyproject_toml, config_settings)

    assert settings.cmake.minimum_version == "3.15"
    assert settings.ninja.minimum_version == "1.5"
    assert settings.logging.level == "WARNING"


def test_skbuild_settings_envvar(tmp_path, monkeypatch):
    monkeypatch.setenv("SKBUILD_CMAKE_MINIMUM_VERSION", "3.16")
    monkeypatch.setenv("SKBUILD_NINJA_MINIMUM_VERSION", "1.1")
    monkeypatch.setenv("SKBUILD_LOGGING_LEVEL", "DEBUG")

    pyproject_toml = tmp_path / "pyproject.toml"
    pyproject_toml.write_text("", encoding="utf-8")

    config_settings: dict[str, list[str] | str] = {}

    settings = read_settings(pyproject_toml, config_settings)

    assert settings.cmake.minimum_version == "3.16"
    assert settings.ninja.minimum_version == "1.1"
    assert settings.logging.level == "DEBUG"


def test_skbuild_settings_config_settings(tmp_path):
    pyproject_toml = tmp_path / "pyproject.toml"
    pyproject_toml.write_text("", encoding="utf-8")

    config_settings = {
        "scikit-build.cmake.minimum-version": "3.17",
        "scikit-build.ninja.minimum-version": "1.2",
        "scikit-build.logging.level": "INFO",
    }

    settings = read_settings(pyproject_toml, config_settings)

    assert settings.cmake.minimum_version == "3.17"
    assert settings.ninja.minimum_version == "1.2"
    assert settings.logging.level == "INFO"


def test_skbuild_settings_pyproject_toml(tmp_path):
    pyproject_toml = tmp_path / "pyproject.toml"
    pyproject_toml.write_text(
        textwrap.dedent(
            """\
            [tool.scikit-build]
            cmake.minimum-version = "3.18"
            ninja.minimum-version = "1.3"
            logging.level = "ERROR"
            """
        ),
        encoding="utf-8",
    )

    config_settings: dict[str, list[str] | str] = {}

    settings = read_settings(pyproject_toml, config_settings)

    assert settings.cmake.minimum_version == "3.18"
    assert settings.ninja.minimum_version == "1.3"
    assert settings.logging.level == "ERROR"
