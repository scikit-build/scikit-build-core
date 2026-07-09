from __future__ import annotations

from pathlib import Path
from textwrap import dedent

import pytest

from scikit_build_core.settings.skbuild_read_settings import SettingsReader

DIR = Path(__file__).parent.resolve()

DECLARATION = dedent(
    """\
    [tool.scikit-build.config-setting."zmq.prefix"]
    help = "Prefix to search for libzmq"

    [tool.scikit-build.config-setting."zmq.libzmq"]
    help = "Where libzmq comes from"
    default = "system"
    """
)


def write_pyproject(tmp_path: Path, text: str) -> Path:
    pyproject_toml = tmp_path / "pyproject.toml"
    pyproject_toml.write_text(text, encoding="utf-8")
    return pyproject_toml


# ---------------------------------------------------------------------------
# Declaration parsing
# ---------------------------------------------------------------------------


def test_declaration_minimal(tmp_path: Path):
    pyproject_toml = write_pyproject(tmp_path, DECLARATION)
    settings_reader = SettingsReader.from_file(pyproject_toml)
    settings_reader.validate_may_exit()
    decls = settings_reader.config_setting_decls
    assert set(decls) == {"zmq.prefix", "zmq.libzmq"}
    assert decls["zmq.prefix"].help == "Prefix to search for libzmq"
    assert decls["zmq.libzmq"].default == "system"


@pytest.mark.parametrize(
    "entry",
    [
        pytest.param('"zmq.prefix" = {unknown = "x"}', id="unknown-key"),
        pytest.param('"zmq.prefix" = {cmake = "ZMQ_PREFIX"}', id="no-cmake-alias"),
        pytest.param('"zmq.prefix" = {type = "int"}', id="bad-type"),
        pytest.param('prefix = {help = "no dot"}', id="dotless-name"),
        pytest.param('"cmake.prefix" = {help = "reserved"}', id="reserved-segment"),
        pytest.param('"skbuild.x" = {help = "reserved"}', id="skbuild-segment"),
        pytest.param(
            '"zmq.libzmq" = {choices = ["bundled"]}', id="removed-choices-key"
        ),
        pytest.param(
            '"zmq.bundled" = {type = "bool", default = "yes"}', id="bad-default-bool"
        ),
        pytest.param('"zmq.prefix" = {default = true}', id="bad-default-str"),
        pytest.param('"zmq.pre fix" = {help = "bad segment"}', id="bad-charset"),
        pytest.param('"zmq.prefix" = "just a string"', id="not-a-table"),
    ],
)
def test_declaration_invalid(tmp_path: Path, entry: str):
    pyproject_toml = write_pyproject(
        tmp_path, f"[tool.scikit-build.config-setting]\n{entry}\n"
    )
    with pytest.raises(SystemExit) as exc:
        SettingsReader.from_file(pyproject_toml)
    assert exc.value.code == 7


# ---------------------------------------------------------------------------
# Strict-config acceptance of declared keys
# ---------------------------------------------------------------------------


def test_declared_key_accepted(tmp_path: Path):
    pyproject_toml = write_pyproject(tmp_path, DECLARATION)
    settings_reader = SettingsReader.from_file(
        pyproject_toml, {"zmq.libzmq": "bundled"}
    )
    settings_reader.validate_may_exit()
    assert settings_reader.custom_config_settings["zmq.libzmq"] == "bundled"


def test_undeclared_key_rejected(tmp_path: Path, capsys: pytest.CaptureFixture[str]):
    pyproject_toml = write_pyproject(tmp_path, "[tool.scikit-build]\n")
    settings_reader = SettingsReader.from_file(
        pyproject_toml, {"zmq.libzmq": "bundled"}
    )
    with pytest.raises(SystemExit) as exc:
        settings_reader.validate_may_exit()
    assert exc.value.code == 7
    out, _ = capsys.readouterr()
    assert "zmq" in out


def test_typo_gets_suggestion(tmp_path: Path, capsys: pytest.CaptureFixture[str]):
    pyproject_toml = write_pyproject(tmp_path, DECLARATION)
    settings_reader = SettingsReader.from_file(pyproject_toml, {"zmq.libzq": "x"})
    with pytest.raises(SystemExit) as exc:
        settings_reader.validate_may_exit()
    assert exc.value.code == 7
    out, _ = capsys.readouterr()
    assert "zmq.libzmq" in out


def test_skbuild_prefixed_custom_key_rejected(tmp_path: Path):
    pyproject_toml = write_pyproject(tmp_path, DECLARATION)
    settings_reader = SettingsReader.from_file(
        pyproject_toml, {"skbuild.zmq.libzmq": "bundled"}
    )
    with pytest.raises(SystemExit) as exc:
        settings_reader.validate_may_exit()
    assert exc.value.code == 7


# ---------------------------------------------------------------------------
# Resolution: env > config-settings > default
# ---------------------------------------------------------------------------

ENV_DECLARATION = dedent(
    """\
    [tool.scikit-build.config-setting."zmq.prefix"]
    help = "Prefix to search for libzmq"
    env = "ZMQ_PREFIX"
    """
)


def test_resolve_from_config_settings(tmp_path: Path):
    pyproject_toml = write_pyproject(tmp_path, ENV_DECLARATION)
    settings_reader = SettingsReader.from_file(pyproject_toml, {"zmq.prefix": "/foo"})
    assert settings_reader.custom_config_settings["zmq.prefix"] == "/foo"


def test_resolve_repeated_config_setting_errors(tmp_path: Path):
    pyproject_toml = write_pyproject(tmp_path, ENV_DECLARATION)
    with pytest.raises(SystemExit):
        SettingsReader.from_file(pyproject_toml, {"zmq.prefix": ["/foo", "/bar"]})


def test_resolve_from_env(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("ZMQ_PREFIX", "/from-env")
    pyproject_toml = write_pyproject(tmp_path, ENV_DECLARATION)
    settings_reader = SettingsReader.from_file(pyproject_toml)
    assert settings_reader.custom_config_settings["zmq.prefix"] == "/from-env"


def test_env_beats_config_settings(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("ZMQ_PREFIX", "/from-env")
    pyproject_toml = write_pyproject(tmp_path, ENV_DECLARATION)
    settings_reader = SettingsReader.from_file(pyproject_toml, {"zmq.prefix": "/foo"})
    assert settings_reader.custom_config_settings["zmq.prefix"] == "/from-env"


def test_default_and_unset(tmp_path: Path):
    pyproject_toml = write_pyproject(tmp_path, DECLARATION)
    settings_reader = SettingsReader.from_file(pyproject_toml)
    assert settings_reader.custom_config_settings["zmq.libzmq"] == "system"
    assert settings_reader.custom_config_settings["zmq.prefix"] is None


BOOL_DECLARATION = dedent(
    """\
    [tool.scikit-build.config-setting."zmq.bundled"]
    type = "bool"
    default = false
    """
)


@pytest.mark.parametrize(
    ("value", "expected"),
    [("ON", True), ("1", True), ("off", False), ("false", False)],
)
def test_bool_type(tmp_path: Path, value: str, expected: bool):
    pyproject_toml = write_pyproject(tmp_path, BOOL_DECLARATION)
    settings_reader = SettingsReader.from_file(pyproject_toml, {"zmq.bundled": value})
    assert settings_reader.custom_config_settings["zmq.bundled"] is expected


def test_bool_type_gpep517_bool(tmp_path: Path):
    pyproject_toml = write_pyproject(tmp_path, BOOL_DECLARATION)
    settings_reader = SettingsReader.from_file(pyproject_toml, {"zmq.bundled": True})
    assert settings_reader.custom_config_settings["zmq.bundled"] is True


# ---------------------------------------------------------------------------
# CMake define binding
# ---------------------------------------------------------------------------


def test_define_reference(tmp_path: Path):
    pyproject_toml = write_pyproject(
        tmp_path,
        DECLARATION
        + dedent(
            """\
            [tool.scikit-build.cmake.define]
            ZMQ_PREFIX = {config-setting = "zmq.prefix"}
            """
        ),
    )
    settings_reader = SettingsReader.from_file(pyproject_toml, {"zmq.prefix": "/foo"})
    assert settings_reader.settings.cmake.define["ZMQ_PREFIX"] == "/foo"


def test_define_reference_unset_dropped(tmp_path: Path):
    pyproject_toml = write_pyproject(
        tmp_path,
        DECLARATION
        + dedent(
            """\
            [tool.scikit-build.cmake.define]
            ZMQ_PREFIX = {config-setting = "zmq.prefix"}
            """
        ),
    )
    settings_reader = SettingsReader.from_file(pyproject_toml)
    assert "ZMQ_PREFIX" not in settings_reader.settings.cmake.define


def test_define_reference_bool(tmp_path: Path):
    pyproject_toml = write_pyproject(
        tmp_path,
        BOOL_DECLARATION
        + dedent(
            """\
            [tool.scikit-build.cmake.define]
            ZMQ_BUNDLED = {config-setting = "zmq.bundled"}
            """
        ),
    )
    settings_reader = SettingsReader.from_file(pyproject_toml, {"zmq.bundled": "on"})
    assert settings_reader.settings.cmake.define["ZMQ_BUNDLED"] == "TRUE"
    settings_reader = SettingsReader.from_file(pyproject_toml)
    assert settings_reader.settings.cmake.define["ZMQ_BUNDLED"] == "FALSE"


def test_define_reference_undeclared(tmp_path: Path):
    pyproject_toml = write_pyproject(
        tmp_path,
        dedent(
            """\
            [tool.scikit-build.cmake.define]
            ZMQ_PREFIX = {config-setting = "zmq.prefix"}
            """
        ),
    )
    with pytest.raises(SystemExit) as exc:
        SettingsReader.from_file(pyproject_toml)
    assert exc.value.code == 7


def test_define_reference_extra_keys(tmp_path: Path):
    pyproject_toml = write_pyproject(
        tmp_path,
        DECLARATION
        + dedent(
            """\
            [tool.scikit-build.cmake.define]
            ZMQ_PREFIX = {config-setting = "zmq.prefix", default = "/dflt"}
            """
        ),
    )
    with pytest.raises(SystemExit) as exc:
        SettingsReader.from_file(pyproject_toml)
    assert exc.value.code == 7


def test_define_conf_beats_toml_reference(tmp_path: Path):
    pyproject_toml = write_pyproject(
        tmp_path,
        DECLARATION
        + dedent(
            """\
            [tool.scikit-build.cmake.define]
            ZMQ_PREFIX = {config-setting = "zmq.prefix"}
            """
        ),
    )
    settings_reader = SettingsReader.from_file(
        pyproject_toml,
        {"zmq.prefix": "/foo", "cmake.define.ZMQ_PREFIX": "/explicit"},
    )
    assert settings_reader.settings.cmake.define["ZMQ_PREFIX"] == "/explicit"


PREFIX_DECLARATION = dedent(
    """\
    [tool.scikit-build.config-setting."zmq.prefix"]
    help = "Prefix to search for libzmq"
    env = "ZMQ_PREFIX"
    """
)


@pytest.mark.parametrize("with_decl", [True, False])
@pytest.mark.parametrize(
    "malformed",
    [
        pytest.param('cmake = "x"', id="cmake"),
        pytest.param('cmake.define = "x"', id="define"),
    ],
)
def test_malformed_cmake_table(tmp_path: Path, malformed: str, with_decl: bool):
    """A non-table cmake value must hit the normal conversion error, not an
    internal AttributeError in the config-setting resolution helpers."""
    content = f"[tool.scikit-build]\n{malformed}\n"
    if with_decl:
        content += PREFIX_DECLARATION
    pyproject_toml = write_pyproject(tmp_path, content)
    with pytest.raises(Exception, match="Failed converting") as exc:
        SettingsReader.from_file(pyproject_toml, {"zmq.prefix": "/foo"})
    assert not isinstance(exc.value, AttributeError)


# ---------------------------------------------------------------------------
# minimum-version gate
# ---------------------------------------------------------------------------


def test_minimum_version_gate_too_old(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
):
    # CI shallow clones report 0.1.devN, tripping the backend-too-old check first
    monkeypatch.setattr(
        "scikit_build_core.settings.skbuild_read_settings.__version__", "1.1.0"
    )
    pyproject_toml = write_pyproject(
        tmp_path,
        'tool.scikit-build.minimum-version = "1.0"\n' + DECLARATION,
    )
    with pytest.raises(SystemExit) as exc:
        SettingsReader.from_file(pyproject_toml)
    assert exc.value.code == 7
    _, err = capsys.readouterr()
    assert "minimum-version must be at least 1.1" in err


def test_minimum_version_gate_ok(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(
        "scikit_build_core.settings.skbuild_read_settings.__version__", "1.1.0"
    )
    pyproject_toml = write_pyproject(
        tmp_path,
        'tool.scikit-build.minimum-version = "1.1"\n' + DECLARATION,
    )
    settings_reader = SettingsReader.from_file(pyproject_toml)
    settings_reader.validate_may_exit()


# ---------------------------------------------------------------------------
# Integration: values reach CMake
# ---------------------------------------------------------------------------


@pytest.mark.configure
@pytest.mark.parametrize("source", ["conf", "env"])
def test_config_settings_reach_cmake(
    source: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    from scikit_build_core.builder.builder import Builder
    from scikit_build_core.cmake import CMake, CMaker

    source_dir = DIR / "packages" / "config_settings"
    binary_dir = tmp_path / "build"

    config_settings: dict[str, str] = {"zmq.libzmq": "bundled"}
    if source == "conf":
        config_settings["zmq.prefix"] = "/opt/zmq"
    else:
        monkeypatch.setenv("ZMQ_PREFIX", "/opt/zmq")

    reader = SettingsReader.from_file(
        source_dir / "pyproject.toml", config_settings, state="wheel"
    )
    reader.validate_may_exit()

    config = CMaker(
        CMake.default_search(),
        source_dir=source_dir,
        build_dir=binary_dir,
        build_type="Release",
    )
    builder = Builder(reader.settings, config)
    builder.configure(defines={})

    configure_log = Path.read_text(binary_dir / "log.txt")
    assert configure_log == dedent(
        """\
        ZMQ_PREFIX = /opt/zmq
        ZMQ_LIBZMQ = bundled
        """
    )
