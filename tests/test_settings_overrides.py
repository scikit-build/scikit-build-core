from __future__ import annotations

import typing
from textwrap import dedent

import pytest

from scikit_build_core.settings.skbuild_read_settings import SettingsReader, regex_match

if typing.TYPE_CHECKING:
    from pathlib import Path


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

    settings_reader = SettingsReader.from_file(pyproject_toml)
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

    settings_reader = SettingsReader.from_file(pyproject_toml)
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


@pytest.mark.parametrize("implementation_name", ["cpython", "pypy"])
@pytest.mark.parametrize("platform_system", ["darwin", "linux"])
def test_skbuild_overrides_any(
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
            if.any = {implementation-name = "pypy", platform-system = "darwin"}
            editable.verbose = false
            install.components = ["headers"]

            [[tool.scikit-build.overrides]]
            if.any.implementation-name = "cpython"
            if.any.platform-system = "darwin"
            install.components = ["bindings"]
            """
        ),
        encoding="utf-8",
    )

    settings_reader = SettingsReader.from_file(pyproject_toml)
    settings = settings_reader.settings

    if implementation_name == "cpython" or platform_system == "darwin":
        assert settings.editable.verbose == (
            platform_system == "linux" and implementation_name == "cpython"
        )
        assert settings.install.components == ["bindings"]
    elif implementation_name == "pypy" or platform_system == "darwin":
        assert not settings.editable.verbose
        assert settings.install.components == ["headers"]
    else:
        assert settings.editable.verbose
        assert not settings.install.components


@pytest.mark.parametrize("python_version", ["3.9", "3.10"])
@pytest.mark.parametrize("implementation_name", ["cpython", "pypy"])
@pytest.mark.parametrize("platform_system", ["darwin", "linux"])
def test_skbuild_overrides_any_mixed(
    implementation_name: str,
    platform_system: str,
    python_version: str,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.setattr(
        "sys.implementation", type("Mock", (), {"name": implementation_name})
    )
    monkeypatch.setattr("sys.platform", platform_system)
    monkeypatch.setattr("sys.version_info", (*map(int, python_version.split(".")), 0))

    pyproject_toml = tmp_path / "pyproject.toml"
    pyproject_toml.write_text(
        dedent(
            """\
            [[tool.scikit-build.overrides]]
            if.any = {implementation-name = "pypy", platform-system = "darwin"}
            if.python-version = ">=3.10"
            editable.verbose = false
            install.components = ["headers"]
            """
        ),
        encoding="utf-8",
    )

    settings_reader = SettingsReader.from_file(pyproject_toml)
    settings = settings_reader.settings

    if python_version == "3.10" and (
        implementation_name == "pypy" or platform_system == "darwin"
    ):
        assert not settings.editable.verbose
        assert settings.install.components == ["headers"]
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

    settings_reader = SettingsReader.from_file(pyproject_toml)
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

    settings_reader = SettingsReader.from_file(pyproject_toml)
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

    with pytest.raises(KeyError, match="At least one 'if' override must be provided"):
        SettingsReader.from_file(pyproject_toml)


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

    with pytest.raises(KeyError, match="At least one 'if' override must be provided"):
        SettingsReader.from_file(pyproject_toml)


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

    settings = SettingsReader.from_file(pyproject_toml)
    with pytest.raises(SystemExit):
        settings.validate_may_exit()


@pytest.mark.parametrize("regex", ["is", "this", "^this", "string$"])
def test_regex_match(regex: str):
    assert regex_match("this_is_a_string", regex)


@pytest.mark.parametrize("regex", ["^string", "this$", "other"])
def test_not_regex_match(regex: str):
    assert not regex_match("this_is_a_string", regex)


@pytest.mark.parametrize("envvar", ["BAR", "", None])
def test_skbuild_env(
    envvar: str | None, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    if envvar is None:
        monkeypatch.delenv("FOO", raising=False)
    else:
        monkeypatch.setenv("FOO", envvar)

    pyproject_toml = tmp_path / "pyproject.toml"
    pyproject_toml.write_text(
        dedent(
            """\
            [[tool.scikit-build.overrides]]
            if.env.FOO = "BAR"
            sdist.cmake = true
            """
        ),
        encoding="utf-8",
    )

    settings_reader = SettingsReader.from_file(pyproject_toml)
    settings = settings_reader.settings

    if envvar == "BAR":
        assert settings.sdist.cmake
    else:
        assert not settings.sdist.cmake


@pytest.mark.parametrize("envvar", ["tRUE", "3", "0", "", None])
def test_skbuild_env_bool(
    envvar: str | None, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    if envvar is None:
        monkeypatch.delenv("FOO", raising=False)
    else:
        monkeypatch.setenv("FOO", envvar)

    pyproject_toml = tmp_path / "pyproject.toml"
    pyproject_toml.write_text(
        dedent(
            """\
            [[tool.scikit-build.overrides]]
            if.env.FOO = true
            sdist.cmake = true
            """
        ),
        encoding="utf-8",
    )

    settings_reader = SettingsReader.from_file(pyproject_toml)
    settings = settings_reader.settings

    if envvar in {"tRUE", "3"}:
        assert settings.sdist.cmake
    else:
        assert not settings.sdist.cmake


@pytest.mark.parametrize("foo", ["true", "false"])
@pytest.mark.parametrize("bar", ["true", "false"])
@pytest.mark.parametrize("any", [True, False])
def test_skbuild_env_bool_all_any(
    foo: str, bar: str, any: bool, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    monkeypatch.setenv("FOO", foo)
    monkeypatch.setenv("BAR", bar)

    any_str = ".any" if any else ""
    pyproject_toml = tmp_path / "pyproject.toml"
    pyproject_toml.write_text(
        dedent(
            f"""\
            [[tool.scikit-build.overrides]]
            if{any_str}.env.FOO = true
            if{any_str}.env.BAR = true
            sdist.cmake = true
            """
        ),
        encoding="utf-8",
    )

    settings_reader = SettingsReader.from_file(pyproject_toml)
    settings = settings_reader.settings

    if (foo == "true" and bar == "true") or (any and (foo == "true" or bar == "true")):
        assert settings.sdist.cmake
    else:
        assert not settings.sdist.cmake


@pytest.mark.parametrize("state", ["wheel", "sdist"])
def test_skbuild_overrides_state(state: str, tmp_path: Path):
    pyproject_toml = tmp_path / "pyproject.toml"
    pyproject_toml.write_text(
        dedent(
            f"""\
            [[tool.scikit-build.overrides]]
            if.state = "{state}"
            experimental = true
            """
        ),
        encoding="utf-8",
    )

    settings_reader = SettingsReader.from_file(pyproject_toml, state="wheel")
    settings = settings_reader.settings

    if state == "wheel":
        assert settings.experimental
    else:
        assert not settings.experimental


@pytest.mark.parametrize("inherit", ["none", "append", "prepend"])
def test_skbuild_overrides_inherit(inherit: str, tmp_path: Path):
    pyproject_toml = tmp_path / "pyproject.toml"
    pyproject_toml.write_text(
        dedent(
            f"""\
            [tool.scikit-build]
            cmake.args = ["a", "b"]
            cmake.targets = ["a", "b"]
            wheel.packages = ["a", "b"]
            wheel.license-files = ["a.txt", "b.txt"]
            wheel.exclude = ["x", "y"]
            install.components = ["a", "b"]
            cmake.define = {{a="A", b="B"}}

            [[tool.scikit-build.overrides]]
            if.state = "wheel"
            inherit.cmake.args = "{inherit}"
            inherit.cmake.targets = "{inherit}"
            inherit.wheel.packages = "{inherit}"
            inherit.wheel.license-files = "{inherit}"
            inherit.wheel.exclude = "{inherit}"
            inherit.install.components = "{inherit}"
            inherit.cmake.define = "{inherit}"
            cmake.args = ["c", "d"]
            cmake.targets = ["c", "d"]
            wheel.packages = ["c", "d"]
            wheel.license-files = ["c.txt", "d.txt"]
            wheel.exclude = ["xx", "yy"]
            install.components = ["c", "d"]
            cmake.define = {{b="X", c="C"}}
            """
        ),
        encoding="utf-8",
    )

    settings_reader = SettingsReader.from_file(pyproject_toml, state="wheel")
    settings = settings_reader.settings

    if inherit == "none":
        assert settings.cmake.args == ["c", "d"]
        assert settings.cmake.targets == ["c", "d"]
        assert settings.wheel.packages == ["c", "d"]
        assert settings.wheel.license_files == ["c.txt", "d.txt"]
        assert settings.wheel.exclude == ["xx", "yy"]
        assert settings.install.components == ["c", "d"]
        assert settings.cmake.define == {"b": "X", "c": "C"}
    elif inherit == "append":
        assert settings.cmake.args == ["a", "b", "c", "d"]
        assert settings.cmake.targets == ["a", "b", "c", "d"]
        assert settings.wheel.packages == ["a", "b", "c", "d"]
        assert settings.wheel.license_files == ["a.txt", "b.txt", "c.txt", "d.txt"]
        assert settings.wheel.exclude == ["x", "y", "xx", "yy"]
        assert settings.install.components == ["a", "b", "c", "d"]
        assert settings.cmake.define == {"a": "A", "b": "X", "c": "C"}
    elif inherit == "prepend":
        assert settings.cmake.args == ["c", "d", "a", "b"]
        assert settings.cmake.targets == ["c", "d", "a", "b"]
        assert settings.wheel.packages == ["c", "d", "a", "b"]
        assert settings.wheel.license_files == ["c.txt", "d.txt", "a.txt", "b.txt"]
        assert settings.wheel.exclude == ["xx", "yy", "x", "y"]
        assert settings.install.components == ["c", "d", "a", "b"]
        assert settings.cmake.define == {"a": "A", "b": "B", "c": "C"}


@pytest.mark.parametrize("from_sdist", [True, False])
def test_skbuild_overrides_from_sdist(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, from_sdist: bool
):
    pyproject_toml = (
        tmp_path / ("from_sdist" if from_sdist else "not_from_sdist") / "pyproject.toml"
    )
    pyproject_toml.parent.mkdir(exist_ok=True)
    pyproject_toml.write_text(
        dedent(
            """\
            [tool.scikit-build]
            cmake.version = ">=3.15"
            wheel.cmake = false
            sdist.cmake = false

            [[tool.scikit-build.overrides]]
            if.from-sdist = false
            wheel.cmake = true

            [[tool.scikit-build.overrides]]
            if.from-sdist = true
            sdist.cmake = true
            """
        ),
        encoding="utf-8",
    )

    if from_sdist:
        pyproject_toml.parent.joinpath("PKG-INFO").touch(exist_ok=True)

    monkeypatch.chdir(pyproject_toml.parent)

    settings_reader = SettingsReader.from_file(pyproject_toml, state="wheel")
    settings = settings_reader.settings

    assert settings.wheel.cmake != from_sdist
    assert settings.sdist.cmake == from_sdist
