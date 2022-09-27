import textwrap

from scikit_build_core.settings.convert import read_cmake_settings


def test_cmake_settings_default(tmp_path):
    pyproject_toml = tmp_path / "pyproject.toml"
    pyproject_toml.write_text("", encoding="utf-8")

    config_settings = {}

    settings = read_cmake_settings(pyproject_toml, config_settings)

    assert settings.min_version == "3.15"


def test_cmake_settings_envvar(tmp_path, monkeypatch):
    monkeypatch.setenv("SKBUILD_MIN_VERSION", "3.16")

    pyproject_toml = tmp_path / "pyproject.toml"
    pyproject_toml.write_text("", encoding="utf-8")

    config_settings = {}

    settings = read_cmake_settings(pyproject_toml, config_settings)

    assert settings.min_version == "3.16"


def test_cmake_settings_config_settings(tmp_path):
    pyproject_toml = tmp_path / "pyproject.toml"
    pyproject_toml.write_text("", encoding="utf-8")

    config_settings = {"cmake.min-version": "3.17"}

    settings = read_cmake_settings(pyproject_toml, config_settings)

    assert settings.min_version == "3.17"


def test_cmake_settings_pyproject_toml(tmp_path):
    pyproject_toml = tmp_path / "pyproject.toml"
    pyproject_toml.write_text(
        textwrap.dedent(
            """\
            [tool.cmake]
            min-version = "3.18"
            """
        ),
        encoding="utf-8",
    )

    config_settings = {}

    settings = read_cmake_settings(pyproject_toml, config_settings)

    assert settings.min_version == "3.18"
