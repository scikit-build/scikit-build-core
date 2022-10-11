import textwrap

from scikit_build_core.settings.cmake_settings import read_settings


def test_cmake_settings_default(tmp_path):
    pyproject_toml = tmp_path / "pyproject.toml"
    pyproject_toml.write_text("", encoding="utf-8")

    config_settings = {}

    settings = read_settings(pyproject_toml, config_settings)

    assert settings.cmake.min_version == "3.15"
    assert settings.ninja.min_version == "0.0"


def test_cmake_settings_envvar(tmp_path, monkeypatch):
    monkeypatch.setenv("SKBUILD_CMAKE_MIN_VERSION", "3.16")
    monkeypatch.setenv("SKBUILD_NINJA_MIN_VERSION", "1.1")

    pyproject_toml = tmp_path / "pyproject.toml"
    pyproject_toml.write_text("", encoding="utf-8")

    config_settings = {}

    settings = read_settings(pyproject_toml, config_settings)

    assert settings.cmake.min_version == "3.16"
    assert settings.ninja.min_version == "1.1"


def test_cmake_settings_config_settings(tmp_path):
    pyproject_toml = tmp_path / "pyproject.toml"
    pyproject_toml.write_text("", encoding="utf-8")

    config_settings = {
        "scikit-build.cmake.min-version": "3.17",
        "scikit-build.ninja.min-version": "1.2",
    }

    settings = read_settings(pyproject_toml, config_settings)

    assert settings.cmake.min_version == "3.17"
    assert settings.ninja.min_version == "1.2"


def test_cmake_settings_pyproject_toml(tmp_path):
    pyproject_toml = tmp_path / "pyproject.toml"
    pyproject_toml.write_text(
        textwrap.dedent(
            """\
            [tool.scikit-build]
            cmake.min-version = "3.18"
            ninja.min-version = "1.3"
            """
        ),
        encoding="utf-8",
    )

    config_settings = {}

    settings = read_settings(pyproject_toml, config_settings)

    assert settings.cmake.min_version == "3.18"
    assert settings.ninja.min_version == "1.3"
