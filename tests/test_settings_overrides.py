from pathlib import Path
from textwrap import dedent

import pytest

from scikit_build_core.settings.skbuild_read_settings import SettingsReader, regex_match


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
            if = {python-version = ">=3.10"}
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
            if = {implementation-name = "pypy", platform-system = "darwin"}
            editable.verbose = false
            install.components = ["headers"]

            [[tool.scikit-build.overrides]]
            if.implementation-name = "cpython"
            if.platform-system = "darwin"
            install.components = ["bindings"]
            """
        ),
        encoding="utf-8",
    )

    settings_reader = SettingsReader.from_file(pyproject_toml, {})
    settings = settings_reader.settings

    if implementation_name == "pypy" and platform_system == "darwin":
        assert not settings.editable.verbose
        assert settings.install.components == ["headers"]
    elif implementation_name == "cpython" and platform_system == "darwin":
        assert settings.editable.verbose
        assert settings.install.components == ["bindings"]
    else:
        assert settings.editable.verbose
        assert not settings.install.components


@pytest.mark.parametrize("platform_node", ["thismatch", "matchthat"])
def test_skbuild_overrides_platnode(
    platform_node: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    monkeypatch.setattr("platform.node", lambda: platform_node)
    pyproject_toml = tmp_path / "pyproject.toml"
    pyproject_toml.write_text(
        dedent(
            """\
            [[tool.scikit-build.overrides]]
            if.platform-node = "^match"
            experimental = true
            """
        ),
        encoding="utf-8",
    )

    settings_reader = SettingsReader.from_file(pyproject_toml, {})
    settings = settings_reader.settings

    if platform_node == "matchthat":
        assert settings.experimental
    else:
        assert not settings.experimental


@pytest.mark.parametrize("platform_machine", ["x86_64", "x86_32", "other"])
def test_skbuild_overrides_regex(
    platform_machine: str,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.setattr("platform.machine", lambda: platform_machine)

    pyproject_toml = tmp_path / "pyproject.toml"
    pyproject_toml.write_text(
        dedent(
            """\
            [tool.scikit-build]
            install.components = ["default"]

            [[tool.scikit-build.overrides]]
            if = {platform_machine = "x86_.*"}
            install.components = ["headers"]

            [[tool.scikit-build.overrides]]
            if = {platform_machine = "x86_32"}
            install.components = ["headers_32"]
            """
        ),
        encoding="utf-8",
    )

    settings_reader = SettingsReader.from_file(pyproject_toml, {})
    settings = settings_reader.settings

    if platform_machine == "x86_64":
        assert settings.install.components == ["headers"]
    elif platform_machine == "x86_32":
        assert settings.install.components == ["headers_32"]
    else:
        assert settings.install.components == ["default"]


def test_skbuild_overrides_no_if(
    tmp_path: Path,
):
    pyproject_toml = tmp_path / "pyproject.toml"
    pyproject_toml.write_text(
        dedent(
            """\
            [[tool.scikit-build.overrides]]
            minimum-version="0.1"
            """
        ),
        encoding="utf-8",
    )

    with pytest.raises(KeyError):
        SettingsReader.from_file(pyproject_toml, {})


def test_skbuild_overrides_empty_if(
    tmp_path: Path,
):
    pyproject_toml = tmp_path / "pyproject.toml"
    pyproject_toml.write_text(
        dedent(
            """\
            [[tool.scikit-build.overrides]]
            if = {}
            minimum-version="0.1"
            """
        ),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="At least one override must be provided"):
        SettingsReader.from_file(pyproject_toml, {})


def test_skbuild_overrides_invalid_key(
    tmp_path: Path,
):
    pyproject_toml = tmp_path / "pyproject.toml"
    pyproject_toml.write_text(
        dedent(
            """\
            [[tool.scikit-build.overrides]]
            if = {python_version = ">=3"}
            invalid-key = "Hi"
            """
        ),
        encoding="utf-8",
    )

    settings = SettingsReader.from_file(pyproject_toml, {})
    with pytest.raises(SystemExit):
        settings.validate_may_exit()


@pytest.mark.parametrize("regex", ["is", "this", "^this", "string$"])
def test_regex_match(regex: str):
    assert regex_match("this_is_a_string", regex)


@pytest.mark.parametrize("regex", ["^string", "this$", "other"])
def test_not_regex_match(regex: str):
    assert not regex_match("this_is_a_string", regex)
