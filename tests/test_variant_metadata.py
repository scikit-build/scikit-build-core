from __future__ import annotations

import json
from textwrap import dedent
from typing import Any

import pytest

from scikit_build_core._compat import tomllib
from scikit_build_core.settings.skbuild_read_settings import SettingsReader

TYPE_CHECKING = False
if TYPE_CHECKING:
    from pathlib import Path

PLUGIN = """\
import json

def dynamic_metadata(settings, project):
    props = json.dumps(settings["props"], sort_keys=True)
    return {"dependencies": [f"runtime-{settings['label']}"], "description": props}

def get_requires_for_dynamic_metadata(settings):
    return [f"build-{settings['label']}"]
"""

PROJECT = dedent(
    """\
    [project]
    name = "pkg"
    version = "1.0"
    dynamic = ["dependencies", "description"]

    [variant.variants.cu130]
    nvidia.cuda_version_lower_bound = ["13.0"]
    nvidia.sm_arch = ["90", "100"]

    [[tool.dynamic-metadata]]
    provider = {path = "plugins", module = "variant_label_plugin"}
    label = "none"
    props = {}
    tool.scikit-build.variant-label = "label"
    tool.scikit-build.variant-properties = "props"
    """
)

CU130 = {"nvidia": {"cuda_version_lower_bound": ["13.0"], "sm_arch": ["90", "100"]}}


def write_pyproject(tmp_path: Path, text: str) -> Path:
    pyproject_toml = tmp_path / "pyproject.toml"
    pyproject_toml.write_text(text, encoding="utf-8")
    return pyproject_toml


@pytest.fixture
def project(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.chdir(tmp_path)
    plugins = tmp_path / "plugins"
    plugins.mkdir()
    plugins.joinpath("variant_label_plugin.py").write_text(PLUGIN, encoding="utf-8")
    return write_pyproject(tmp_path, PROJECT)


def _conf(label: str | None) -> dict[str, str]:
    return {} if label is None else {"experimental": "true", "variant-label": label}


def _metadata(pyproject_toml: Path, reader: SettingsReader) -> Any:
    from scikit_build_core.build.metadata import get_standard_metadata

    with pyproject_toml.open("rb") as f:
        pyproject = tomllib.load(f)
    return get_standard_metadata(
        pyproject,
        reader.settings,
        build_state="wheel",
        dynamic_metadata_entries=reader.dynamic_metadata,
    )


@pytest.mark.parametrize(
    ("label", "props"),
    [("cu130", CU130), ("null", {}), (None, {})],
    ids=["cu130", "null", "no-variant"],
)
def test_variant_reaches_provider(
    project: Path, label: str | None, props: dict[str, Any]
):
    from scikit_build_core.builder.get_requires import GetRequires

    reader = SettingsReader.from_file(project, _conf(label), state="wheel")
    reader.validate_may_exit()
    assert reader.dynamic_metadata == [
        {
            "provider": {"path": "plugins", "module": "variant_label_plugin"},
            "label": label or "none",
            "props": props,
        }
    ]

    metadata = _metadata(project, reader)
    assert [str(d) for d in metadata.dependencies] == [f"runtime-{label or 'none'}"]
    assert metadata.description == json.dumps(props, sort_keys=True)

    requires = GetRequires.from_config_settings(_conf(label), state="wheel")
    assert f"build-{label or 'none'}" in set(requires.dynamic_metadata())


def test_variant_properties_are_copies(project: Path):
    reader = SettingsReader.from_file(project, _conf("cu130"))
    reader.dynamic_metadata[0]["props"]["nvidia"]["sm_arch"].append("120")
    assert reader.variant["variants"]["cu130"] == CU130


def test_variant_label_only(project: Path):
    text = PROJECT.replace('tool.scikit-build.variant-properties = "props"\n', "")
    reader = SettingsReader.from_file(
        write_pyproject(project.parent, text), _conf("cu130")
    )
    assert reader.dynamic_metadata[0]["label"] == "cu130"
    assert reader.dynamic_metadata[0]["props"] == {}


def test_variant_missing_entry(project: Path, capsys: pytest.CaptureFixture[str]):
    with pytest.raises(SystemExit):
        SettingsReader.from_file(project, _conf("cu999"))
    _, err = capsys.readouterr()
    assert "cu999" in err
    assert "[variant.variants.cu999]" in err


@pytest.mark.parametrize(
    ("value", "match"),
    [
        ("tool.scikit-build.variant-label = 1", "variant-label must be a string"),
        (
            'tool.scikit-build.variant-label = "provider"',
            "may not set 'provider'",
        ),
        (
            'tool.scikit-build.variant-label = "props"',
            "both set 'props'",
        ),
        (
            dedent(
                """\
                tool.scikit-build.variant-label = "label"
                tool.scikit-build.config-setting.label = "pkg.label"
                """
            ),
            "also set by variant-label",
        ),
    ],
)
def test_variant_mapping_invalid(
    project: Path,
    capsys: pytest.CaptureFixture[str],
    value: str,
    match: str,
):
    text = PROJECT.replace(
        'tool.scikit-build.variant-label = "label"\n', value + "\n"
    ).replace(
        "[project]",
        '[tool.scikit-build.config-setting."pkg.label"]\n\n[project]',
    )
    with pytest.raises(SystemExit):
        SettingsReader.from_file(write_pyproject(project.parent, text))
    _, err = capsys.readouterr()
    assert "tool.dynamic-metadata[0].tool.scikit-build" in err
    assert match in err


def test_variant_legacy_metadata_not_supported(project: Path):
    # The legacy table has no reserved tool key, so the plugin gets it as-is.
    legacy_variant_plugin = dedent(
        """\
        def dynamic_metadata(field, settings):
            assert set(settings) == {"label"}
            return [f"runtime-{settings['label']}"]
        """
    )
    project.parent.joinpath("plugins", "legacy_variant_plugin.py").write_text(
        legacy_variant_plugin, encoding="utf-8"
    )
    text = dedent(
        """\
        [project]
        name = "pkg"
        version = "1.0"
        dynamic = ["dependencies"]

        [variant.variants.cu130]
        nvidia.sm_arch = ["90"]

        [tool.scikit-build.metadata.dependencies]
        provider = "legacy_variant_plugin"
        provider-path = "plugins"
        label = "none"
        """
    )
    pyproject_toml = write_pyproject(project.parent, text)
    reader = SettingsReader.from_file(pyproject_toml, _conf("cu130"))
    metadata = _metadata(pyproject_toml, reader)
    assert [str(d) for d in metadata.dependencies] == ["runtime-none"]


@pytest.mark.parametrize("minimum_version", ["1.1", "1.2"])
def test_variant_mapping_minimum_version(
    project: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    minimum_version: str,
):
    monkeypatch.setattr(
        "scikit_build_core.settings.skbuild_read_settings.__version__", "1.2.0"
    )
    pyproject_toml = write_pyproject(
        project.parent,
        f'tool.scikit-build.minimum-version = "{minimum_version}"\n' + PROJECT,
    )
    if minimum_version == "1.2":
        SettingsReader.from_file(pyproject_toml).validate_may_exit()
        return
    with pytest.raises(SystemExit) as exc:
        SettingsReader.from_file(pyproject_toml)
    assert exc.value.code == 7
    _, err = capsys.readouterr()
    assert "minimum-version must be at least 1.2" in err
