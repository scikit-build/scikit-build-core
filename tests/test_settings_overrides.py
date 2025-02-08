from __future__ import annotations

import sysconfig
import typing
from pathlib import Path
from textwrap import dedent

import pytest

import scikit_build_core.settings.skbuild_overrides
from scikit_build_core.settings.skbuild_overrides import regex_match
from scikit_build_core.settings.skbuild_read_settings import SettingsReader

if typing.TYPE_CHECKING:
    from pytest_subprocess import FakeProcess


class VersionInfo(typing.NamedTuple):
    major: int
    minor: int
    micro: int
    releaselevel: str = "final"


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


@pytest.mark.parametrize("implementation_version", ["7.3.14", "7.3.15"])
def test_skbuild_overrides_implver(
    implementation_version: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    monkeypatch.setattr("sys.implementation.name", "pypy")
    monkeypatch.setattr(
        "sys.implementation.version",
        VersionInfo(*(int(x) for x in implementation_version.split("."))),  # type: ignore[arg-type]
    )
    pyproject_toml = tmp_path / "pyproject.toml"
    pyproject_toml.write_text(
        dedent(
            """\
            [[tool.scikit-build.overrides]]
            if.implementation-name = "pypy"
            if.implementation-version = ">=7.3.15"
            experimental = true
            """
        ),
        encoding="utf-8",
    )

    settings_reader = SettingsReader.from_file(pyproject_toml)
    settings = settings_reader.settings

    if implementation_version == "7.3.15":
        assert settings.experimental
    else:
        assert not settings.experimental


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
    print(settings_reader.overrides)

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


@pytest.mark.parametrize("envvar", ["random", "FalSE", "", "0", None])
def test_skbuild_env_negative_bool(
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
            if.env.FOO = false
            sdist.cmake = true
            """
        ),
        encoding="utf-8",
    )

    settings_reader = SettingsReader.from_file(pyproject_toml)
    settings = settings_reader.settings

    if envvar in {"random"}:
        assert not settings.sdist.cmake
    else:
        assert settings.sdist.cmake


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


def test_failed_retry(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    pyproject_toml = tmp_path / "pyproject.toml"
    pyproject_toml.write_text(
        dedent(
            """\
            [tool.scikit-build]
            wheel.cmake = false
            sdist.cmake = false

            [[tool.scikit-build.overrides]]
            if.failed = true
            wheel.cmake = true

            [[tool.scikit-build.overrides]]
            if.failed = false
            sdist.cmake = true
            """
        ),
        encoding="utf-8",
    )

    monkeypatch.chdir(tmp_path)

    settings_reader = SettingsReader.from_file(pyproject_toml, retry=False)
    settings = settings_reader.settings
    assert not settings.wheel.cmake
    assert settings.sdist.cmake

    settings_reader = SettingsReader.from_file(pyproject_toml, retry=True)
    settings = settings_reader.settings
    assert settings.wheel.cmake
    assert not settings.sdist.cmake


@pytest.mark.parametrize("sys_tag", ["win32", "linux"])
def test_wheel_platform(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, sys_tag: str):
    pyproject_toml = tmp_path / "pyproject.toml"
    pyproject_toml.write_text(
        dedent(
            """\
            [tool.scikit-build]
            wheel.cmake = false

            [[tool.scikit-build.overrides]]
            if.cmake-wheel = true
            wheel.cmake = true
            """
        ),
        encoding="utf-8",
    )

    monkeypatch.chdir(tmp_path)

    monkeypatch.setattr("packaging.tags.sys_tags", lambda: [sys_tag])

    settings_reader = SettingsReader.from_file(pyproject_toml, retry=False)
    settings = settings_reader.settings
    assert settings.wheel.cmake == (sys_tag == "win32")


@pytest.mark.parametrize("cmake_version", ["3.21", "3.27"])
@pytest.mark.usefixtures("protect_get_requires")
def test_system_cmake(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    cmake_version: str | None,
    fp: FakeProcess,
) -> None:
    if cmake_version:
        fp.register(
            [Path("cmake/path"), "-E", "capabilities"],
            stdout=f'{{"version":{{"string": "{cmake_version}"}}}}',
        )

    pyproject_toml = tmp_path / "pyproject.toml"
    pyproject_toml.write_text(
        dedent(
            """\
            [tool.scikit-build]
            wheel.cmake = false

            [[tool.scikit-build.overrides]]
            if.system-cmake = ">=3.24"
            wheel.cmake = true
            """
        ),
        encoding="utf-8",
    )

    monkeypatch.chdir(tmp_path)

    settings_reader = SettingsReader.from_file(pyproject_toml, retry=False)
    settings = settings_reader.settings
    assert settings.wheel.cmake == (cmake_version == "3.27")


def test_free_threaded_override(tmp_path: Path):
    pyproject_toml = tmp_path / "pyproject.toml"
    pyproject_toml.write_text(
        dedent(
            """\
            [tool.scikit-build]
            wheel.cmake = false

            [[tool.scikit-build.overrides]]
            if.abi-flags = "t"
            wheel.cmake = true
            """
        )
    )

    settings_reader = SettingsReader.from_file(pyproject_toml, state="wheel")
    settings = settings_reader.settings
    assert settings.wheel.cmake == bool(sysconfig.get_config_var("Py_GIL_DISABLED"))


@pytest.mark.parametrize("version", ["0.9", "0.10"])
def test_skbuild_overrides_version(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, version: str
):
    monkeypatch.setattr(
        scikit_build_core.settings.skbuild_overrides, "__version__", version
    )
    pyproject_toml = tmp_path / "pyproject.toml"
    pyproject_toml.write_text(
        dedent(
            """\
            [tool.scikit-build]
            wheel.cmake = false

            [[tool.scikit-build.overrides]]
            if.scikit-build-version = ">=0.10"
            wheel.cmake = true
            """
        )
    )

    settings_reader = SettingsReader.from_file(pyproject_toml, state="wheel")
    settings = settings_reader.settings
    if version == "0.10":
        assert settings.wheel.cmake
    else:
        assert not settings.wheel.cmake


def test_skbuild_overrides_unmatched_version(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    monkeypatch.setattr(
        scikit_build_core.settings.skbuild_overrides, "__version__", "0.10"
    )
    pyproject_toml = tmp_path / "pyproject.toml"
    pyproject_toml.write_text(
        dedent(
            """\
            [[tool.scikit-build.overrides]]
            if.scikit-build-version = "<0.10"
            if.is-not-real = true
            also-not-real = true
            """
        )
    )

    settings = SettingsReader.from_file(pyproject_toml)
    settings.validate_may_exit()


def test_skbuild_overrides_matched_version_if(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    monkeypatch.setattr(
        scikit_build_core.settings.skbuild_overrides, "__version__", "0.10"
    )
    pyproject_toml = tmp_path / "pyproject.toml"
    pyproject_toml.write_text(
        dedent(
            """\
            [[tool.scikit-build.overrides]]
            if.scikit-build-version = ">=0.10"
            if.is-not-real = true
            """
        )
    )

    with pytest.raises(TypeError, match="is_not_real"):
        SettingsReader.from_file(pyproject_toml)


def test_skbuild_overrides_matched_version_extra(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
):
    monkeypatch.setattr(
        scikit_build_core.settings.skbuild_overrides, "__version__", "0.10"
    )
    pyproject_toml = tmp_path / "pyproject.toml"
    pyproject_toml.write_text(
        dedent(
            """\
            [[tool.scikit-build.overrides]]
            if.scikit-build-version = ">=0.10"
            not-real = true
            """
        )
    )

    settings = SettingsReader.from_file(pyproject_toml)
    with pytest.raises(SystemExit):
        settings.validate_may_exit()

    assert "not-real" in capsys.readouterr().out


def test_skbuild_overrides_matched_version_if_any(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    monkeypatch.setattr(
        scikit_build_core.settings.skbuild_overrides, "__version__", "0.9"
    )
    pyproject_toml = tmp_path / "pyproject.toml"
    pyproject_toml.write_text(
        dedent(
            """\
            [[tool.scikit-build.overrides]]
            if.any.scikit-build-version = ">=0.10"
            if.any.not-real = true
            also-not-real = true
            """
        )
    )

    settings = SettingsReader.from_file(pyproject_toml)
    settings.validate_may_exit()


def test_skbuild_overrides_matched_version_if_any_dual(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    monkeypatch.setattr(
        scikit_build_core.settings.skbuild_overrides, "__version__", "0.9"
    )
    pyproject_toml = tmp_path / "pyproject.toml"
    pyproject_toml.write_text(
        dedent(
            """\
            [[tool.scikit-build.overrides]]
            if.scikit-build-version = ">=0.10"
            if.any.not-real = true
            if.any.python-version = ">=3.8"
            also-not-real = true
            """
        )
    )

    settings = SettingsReader.from_file(pyproject_toml)
    settings.validate_may_exit()


def test_skbuild_overrides_matched_version_if_any_match(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    monkeypatch.setattr(
        scikit_build_core.settings.skbuild_overrides, "__version__", "0.10"
    )
    pyproject_toml = tmp_path / "pyproject.toml"
    pyproject_toml.write_text(
        dedent(
            """\
            [[tool.scikit-build.overrides]]
            if.any.scikit-build-version = ">=0.10"
            if.any.not-real = true
            if.python-version = ">=3.8"
            experimental = true
            """
        )
    )

    with pytest.raises(TypeError, match="not_real"):
        SettingsReader.from_file(pyproject_toml)
