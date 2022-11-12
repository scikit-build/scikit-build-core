from __future__ import annotations

import textwrap

import pytest

from scikit_build_core.settings.skbuild_read_settings import SettingsReader


def test_skbuild_settings_default(tmp_path):
    pyproject_toml = tmp_path / "pyproject.toml"
    pyproject_toml.write_text("", encoding="utf-8")

    config_settings: dict[str, list[str] | str] = {}

    settings_reader = SettingsReader(pyproject_toml, config_settings)
    settings = settings_reader.settings
    assert list(settings_reader.unrecognized_options()) == []

    assert settings.cmake.minimum_version == "3.15"
    assert settings.ninja.minimum_version == "1.5"
    assert settings.ninja.make_fallback
    assert settings.logging.level == "WARNING"
    assert settings.tags.py_abi == ""
    assert not settings.tags.extra
    assert settings.sdist.include == []
    assert settings.sdist.exclude == []
    assert settings.sdist.reproducible
    assert settings.wheel.packages is None
    assert settings.strict_config


def test_skbuild_settings_envvar(tmp_path, monkeypatch):
    monkeypatch.setenv("SKBUILD_CMAKE_MINIMUM_VERSION", "3.16")
    monkeypatch.setenv("SKBUILD_NINJA_MINIMUM_VERSION", "1.1")
    monkeypatch.setenv("SKBUILD_NINJA_MAKE_FALLBACK", "0")
    monkeypatch.setenv("SKBUILD_LOGGING_LEVEL", "DEBUG")
    monkeypatch.setenv("SKBUILD_TAGS_PY_ABI", "cp39-abi3")
    monkeypatch.setenv("SKBUILD_TAGS_EXTRA", "True")
    monkeypatch.setenv("SKBUILD_SDIST_INCLUDE", "a;b; c")
    monkeypatch.setenv("SKBUILD_SDIST_EXCLUDE", "d;e;f")
    monkeypatch.setenv("SKBUILD_SDIST_REPRODUCIBLE", "OFF")
    monkeypatch.setenv("SKBUILD_WHEEL_PACKAGES", "j; k; l")
    monkeypatch.setenv("SKBUILD_STRICT_CONFIG", "0")

    pyproject_toml = tmp_path / "pyproject.toml"
    pyproject_toml.write_text("", encoding="utf-8")

    config_settings: dict[str, list[str] | str] = {}

    settings_reader = SettingsReader(pyproject_toml, config_settings)
    settings = settings_reader.settings
    assert list(settings_reader.unrecognized_options()) == []

    assert settings.cmake.minimum_version == "3.16"
    assert settings.ninja.minimum_version == "1.1"
    assert not settings.ninja.make_fallback
    assert settings.logging.level == "DEBUG"
    assert settings.tags.py_abi == "cp39-abi3"
    assert settings.tags.extra
    assert settings.sdist.include == ["a", "b", "c"]
    assert settings.sdist.exclude == ["d", "e", "f"]
    assert not settings.sdist.reproducible
    assert settings.wheel.packages == ["j", "k", "l"]
    assert not settings.strict_config


def test_skbuild_settings_config_settings(tmp_path):
    pyproject_toml = tmp_path / "pyproject.toml"
    pyproject_toml.write_text("", encoding="utf-8")

    config_settings: dict[str, str | list[str]] = {
        "cmake.minimum-version": "3.17",
        "ninja.minimum-version": "1.2",
        "ninja.make-fallback": "False",
        "logging.level": "INFO",
        "tags.py-abi": "cp39-abi3",
        "tags.extra": "True",
        "sdist.include": ["a", "b", "c"],
        "sdist.exclude": "d;e;f",
        "sdist.reproducible": "false",
        "wheel.packages": ["j", "k", "l"],
        "strict-config": "false",
    }

    settings_reader = SettingsReader(pyproject_toml, config_settings)
    settings = settings_reader.settings
    assert list(settings_reader.unrecognized_options()) == []

    assert settings.cmake.minimum_version == "3.17"
    assert settings.ninja.minimum_version == "1.2"
    assert not settings.ninja.make_fallback
    assert settings.logging.level == "INFO"
    assert settings.tags.py_abi == "cp39-abi3"
    assert settings.tags.extra
    assert settings.sdist.include == ["a", "b", "c"]
    assert settings.sdist.exclude == ["d", "e", "f"]
    assert not settings.sdist.reproducible
    assert settings.wheel.packages == ["j", "k", "l"]
    assert not settings.strict_config


def test_skbuild_settings_pyproject_toml(tmp_path):
    pyproject_toml = tmp_path / "pyproject.toml"
    pyproject_toml.write_text(
        textwrap.dedent(
            """\
            [tool.scikit-build]
            cmake.minimum-version = "3.18"
            ninja.minimum-version = "1.3"
            ninja.make-fallback = false
            logging.level = "ERROR"
            tags.py-abi = "cp39-abi3"
            tags.extra = true
            sdist.include = ["a", "b", "c"]
            sdist.exclude = ["d", "e", "f"]
            sdist.reproducible = false
            wheel.packages = ["j", "k", "l"]
            strict-config = false
            """
        ),
        encoding="utf-8",
    )

    config_settings: dict[str, list[str] | str] = {}

    settings_reader = SettingsReader(pyproject_toml, config_settings)
    settings = settings_reader.settings
    assert list(settings_reader.unrecognized_options()) == []

    assert settings.cmake.minimum_version == "3.18"
    assert settings.ninja.minimum_version == "1.3"
    assert not settings.ninja.make_fallback
    assert settings.logging.level == "ERROR"
    assert settings.tags.py_abi == "cp39-abi3"
    assert settings.tags.extra
    assert settings.sdist.include == ["a", "b", "c"]
    assert settings.sdist.exclude == ["d", "e", "f"]
    assert not settings.sdist.reproducible
    assert settings.wheel.packages == ["j", "k", "l"]
    assert not settings.strict_config


def test_skbuild_settings_pyproject_toml_broken(tmp_path):
    pyproject_toml = tmp_path / "pyproject.toml"
    pyproject_toml.write_text(
        textwrap.dedent(
            """\
            [tool.scikit-build]
            cmake.minimum-verison = "3.18"
            ninja.minimum-version = "1.3"
            ninja.make-fallback = false
            logger.level = "ERROR"
            """
        ),
        encoding="utf-8",
    )

    config_settings: dict[str, list[str] | str] = {}

    settings_reader = SettingsReader(pyproject_toml, config_settings)
    assert list(settings_reader.unrecognized_options()) == [
        "tool.scikit-build.cmake.minimum-verison",
        "tool.scikit-build.logger",
    ]

    with pytest.raises(SystemExit):
        settings_reader.validate_may_exit()


def test_skbuild_settings_pyproject_conf_broken(tmp_path):
    pyproject_toml = tmp_path / "pyproject.toml"
    pyproject_toml.write_text("", encoding="utf-8")

    config_settings: dict[str, str | list[str]] = {
        "cmake.minimum-verison": "3.17",
        "ninja.minimum-version": "1.2",
        "ninja.make-fallback": "False",
        "logger.level": "INFO",
    }

    settings_reader = SettingsReader(pyproject_toml, config_settings)
    assert list(settings_reader.unrecognized_options()) == [
        "cmake.minimum-verison",
        "logger",
    ]

    with pytest.raises(SystemExit):
        settings_reader.validate_may_exit()
