from __future__ import annotations

from pathlib import Path
from textwrap import dedent

import pytest

from scikit_build_core.build._file_processor import each_unignored_file
from scikit_build_core.build.common_wheel_helpers import get_build_dir
from scikit_build_core.builder.wheel_tag import WheelTag
from scikit_build_core.format import pyproject_format
from scikit_build_core.settings.skbuild_read_settings import SettingsReader

DECLARATION = dedent(
    """\
    [tool.scikit-build.config-setting."torch.variant"]
    env = "PYTORCH_VARIANT"

    [tool.scikit-build.config-setting."torch.debug"]
    type = "bool"
    default = false
    """
)

BUILD_DIR = '[tool.scikit-build]\nbuild-dir = "build/{variant}"\n'

FORMAT_KEYS = dedent(
    """\
    [tool.scikit-build.format-keys]
    variant = { config-setting = "torch.variant", default = "cpu" }
    """
)


def read(
    tmp_path: Path, text: str, config_settings: dict[str, str] | None = None
) -> SettingsReader:
    pyproject_toml = tmp_path / "pyproject.toml"
    pyproject_toml.write_text(text, encoding="utf-8")
    reader = SettingsReader.from_file(pyproject_toml, config_settings)
    reader.validate_may_exit()
    return reader


@pytest.mark.parametrize(
    ("config_settings", "env", "expected"),
    [
        ({}, None, "cpu"),
        ({"torch.variant": "cu126"}, None, "cu126"),
        ({}, "rocm7.1", "rocm7.1"),
    ],
)
def test_sources(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    config_settings: dict[str, str],
    env: str | None,
    expected: str,
):
    if env is not None:
        monkeypatch.setenv("PYTORCH_VARIANT", env)
    reader = read(tmp_path, DECLARATION + FORMAT_KEYS, config_settings)
    assert reader.settings.format_keys == {"variant": expected}
    # The default is for the format key only.
    if expected == "cpu":
        assert reader.custom_config_settings["torch.variant"] is None


def test_declaration_default_and_bool(tmp_path: Path):
    text = DECLARATION + dedent(
        """\
        [tool.scikit-build.format-keys]
        debug = { config-setting = "torch.debug" }
        literal = "text"
        """
    )
    assert read(tmp_path, text).settings.format_keys == {
        "debug": "false",
        "literal": "text",
    }
    assert read(tmp_path, text, {"torch.debug": "1"}).settings.format_keys == {
        "debug": "true",
        "literal": "text",
    }


def test_override_sets_key(tmp_path: Path):
    text = (
        DECLARATION
        + FORMAT_KEYS
        + dedent(
            """\
            [[tool.scikit-build.overrides]]
            if.config-setting."torch.debug" = true
            format-keys.variant = "debug"
            """
        )
    )
    assert read(tmp_path, text).settings.format_keys == {"variant": "cpu"}
    reader = read(tmp_path, text, {"torch.debug": "true"})
    assert reader.settings.format_keys == {"variant": "debug"}


def test_build_dir(tmp_path: Path):
    text = BUILD_DIR + DECLARATION + FORMAT_KEYS
    settings = read(tmp_path, text, {"torch.variant": "cu126"}).settings
    build_dir = get_build_dir(
        settings,
        tags=WheelTag.compute_best([]),
        state="wheel",
        editable=False,
        has_cmake=True,
        fallback=tmp_path / "build",
        name="pkg",
    )
    assert build_dir == Path("build/cu126")


def test_build_requires(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    from scikit_build_core.builder.get_requires import GetRequires

    text = (
        '[tool.scikit-build]\nbuild.requires = ["torch-{variant}"]\n'
        + DECLARATION
        + FORMAT_KEYS
    )
    tmp_path.joinpath("pyproject.toml").write_text(text, encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    assert list(GetRequires().dynamic_metadata()) == ["torch-cpu"]
    requires = GetRequires.from_config_settings({"torch.variant": "cu126"})
    assert list(requires.dynamic_metadata()) == ["torch-cu126"]


@pytest.mark.parametrize(
    ("config_settings", "env"),
    [({"format-keys.variant": "cpu"}, None), ({}, "variant=gpu")],
    ids=["config-settings", "env"],
)
def test_dynamic_rejected(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    config_settings: dict[str, str],
    env: str | None,
):
    if env is not None:
        monkeypatch.setenv("SKBUILD_FORMAT_KEYS", env)
    text = BUILD_DIR + DECLARATION + FORMAT_KEYS
    with pytest.raises(SystemExit):
        read(tmp_path, text, config_settings)
    assert "format-keys can only be set in configuration files" in (
        capsys.readouterr().out
    )


def test_overrides_builtin_key(tmp_path: Path) -> None:
    text = '[tool.scikit-build.format-keys]\nstate = "mine"\nname = "other"\n'
    settings = read(tmp_path, text).settings
    formatted = pyproject_format(settings=settings, state="wheel", name="pkg")
    assert "{state}-{name}".format(**formatted) == "mine-other"


@pytest.mark.parametrize(
    "field", ["{variant}", "{variant[1]}", "{variant:0>4}", "{variant!r:>9}"]
)
def test_sdist_excludes_build_dir(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, field: str
) -> None:
    monkeypatch.chdir(tmp_path)
    resolved = Path("out", field.format(variant="cpu"), "cmake")
    resolved.mkdir(parents=True)
    resolved.joinpath("CMakeCache.txt").touch()
    kept = {Path("keep.txt"), Path("out/keep.txt")}
    for path in kept:
        path.touch()

    files = set(
        each_unignored_file(Path(), build_dir=f"out/{field}/cmake", mode="default")
    )
    assert files == kept


@pytest.mark.parametrize(
    ("format_keys", "match"),
    [
        (
            'variant = { config-setting = "torch.other" }',
            "format-keys.variant references undeclared config-setting 'torch.other'",
        ),
        (
            'variant = { config-setting = "torch.variant" }',
            "format-keys.variant: config-setting 'torch.variant' is not set",
        ),
        (
            'variant = { config-setting = "torch.variant", fallback = "cpu" }',
            "format-keys.variant has unrecognized keys: fallback",
        ),
        (
            'variant = { config-setting = "torch.variant", default = true }',
            "format-keys.variant 'default' must be a string",
        ),
        ('variant = { default = "cpu" }', "undeclared config-setting None"),
        ('variant = ["cpu"]', "format-keys.variant must be a string or a table"),
        ("variant = true", "format-keys.variant must be a string or a table"),
        ("variant = 1", "format-keys.variant must be a string or a table"),
        ('"a.b" = "x"', "format-keys.'a.b' must be a valid identifier"),
    ],
)
def test_invalid(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], format_keys: str, match: str
):
    text = DECLARATION + "[tool.scikit-build.format-keys]\n" + format_keys
    with pytest.raises(SystemExit):
        read(tmp_path, text)
    assert match in capsys.readouterr().err.replace("\n", " ")


@pytest.mark.parametrize("value", ["a/b", "a\\b", "..", ".", "", "a/{cpu}"])
def test_build_dir_value_one_path_component(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], value: str
):
    text = BUILD_DIR + DECLARATION + FORMAT_KEYS
    with pytest.raises(SystemExit):
        read(tmp_path, text, {"torch.variant": value})
    assert "must be one path component" in capsys.readouterr().err.replace("\n", " ")
    # Other fields have no limit.
    text = text.replace(
        'build-dir = "build/{variant}"', 'build.requires = ["{variant}"]'
    )
    read(tmp_path, text, {"torch.variant": value})


@pytest.mark.parametrize("field", ["{variant:.0}", "{variant[0]:/>2}"])
def test_build_dir_formatted_one_path_component(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], field: str
):
    text = BUILD_DIR.replace("{variant}", field) + DECLARATION + FORMAT_KEYS
    with pytest.raises(SystemExit):
        read(tmp_path, text)
    assert "must be one path component" in capsys.readouterr().err.replace("\n", " ")


def test_build_dir_unknown_placeholder(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
):
    with pytest.raises(SystemExit):
        read(tmp_path, '[tool.scikit-build]\nbuild-dir = "build/{nope}"\n')
    assert "build-dir: unknown placeholder 'nope'" in capsys.readouterr().err


def test_minimum_version_gate(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
):
    # CI shallow clones report 0.1.devN, tripping the backend-too-old check first
    monkeypatch.setattr(
        "scikit_build_core.settings.skbuild_read_settings.__version__", "1.2.0"
    )
    text = '[tool.scikit-build]\nminimum-version = "1.1"\n' + DECLARATION + FORMAT_KEYS
    with pytest.raises(SystemExit):
        read(tmp_path, text)
    err = capsys.readouterr().err.replace("\n", " ")
    assert "minimum-version must be at least 1.2 to use format-keys" in err
