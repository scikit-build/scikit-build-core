"""
Tests for the ``scikit-build-core.config`` entry-point configuration providers.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

import scikit_build_core._logging
from scikit_build_core._compat.importlib import metadata as compat_metadata
from scikit_build_core.settings import _load_entrypoint_config
from scikit_build_core.settings.skbuild_read_settings import SettingsReader

if TYPE_CHECKING:
    from pathlib import Path


class FakeEntryPoint:
    """Minimal stand-in for ``importlib.metadata.EntryPoint``."""

    def __init__(self, name: str, func: object) -> None:
        self.name = name
        self._func = func

    def load(self) -> object:
        return self._func


@pytest.fixture
def providers(monkeypatch):
    """Register fake ``scikit-build-core.config`` providers.

    Yields a dict; assign ``providers[name] = callable`` to register one.
    """
    registry: dict[str, object] = {}

    def fake_entry_points(*, group: str):
        if group != _load_entrypoint_config.GROUP:
            return []
        return [FakeEntryPoint(name, func) for name, func in registry.items()]

    # The loader resolves entry points through this shared compat module.
    monkeypatch.setattr(compat_metadata, "entry_points", fake_entry_points)
    return registry


def make_reader(tmp_path: Path, body: str = "", **kwargs) -> SettingsReader:
    pyproject_toml = tmp_path / "pyproject.toml"
    pyproject_toml.write_text(body, encoding="utf-8")
    return SettingsReader.from_file(pyproject_toml, {}, **kwargs)


def test_default_provider_applies_when_silent(tmp_path, providers):
    providers["default"] = lambda **_: {
        "cmake": {"build-type": "RelWithDebInfo"},
        "install": {"strip": False},
    }
    settings = make_reader(tmp_path, state="wheel").settings
    assert settings.cmake.build_type == "RelWithDebInfo"
    assert settings.install.strip is False


def test_default_provider_loses_to_pyproject(tmp_path, providers):
    providers["default"] = lambda **_: {"cmake": {"build-type": "RelWithDebInfo"}}
    body = "[tool.scikit-build.cmake]\nbuild-type = 'Debug'\n"
    settings = make_reader(tmp_path, body, state="wheel").settings
    assert settings.cmake.build_type == "Debug"


def test_override_provider_beats_pyproject(tmp_path, providers):
    providers["override"] = lambda **_: {"cmake": {"build-type": "RelWithDebInfo"}}
    body = "[tool.scikit-build.cmake]\nbuild-type = 'Debug'\n"
    settings = make_reader(tmp_path, body, state="wheel").settings
    assert settings.cmake.build_type == "RelWithDebInfo"


def test_override_still_beaten_by_config_settings(tmp_path, providers):
    providers["override"] = lambda **_: {"cmake": {"build-type": "RelWithDebInfo"}}
    pyproject_toml = tmp_path / "pyproject.toml"
    pyproject_toml.write_text("", encoding="utf-8")
    reader = SettingsReader.from_file(
        pyproject_toml, {"cmake.build-type": "Release"}, state="wheel"
    )
    assert reader.settings.cmake.build_type == "Release"


def test_dict_fields_merge_across_levels(tmp_path, providers):
    providers["default"] = lambda **_: {"cmake": {"define": {"FROM_DEFAULT": "1"}}}
    providers["override"] = lambda **_: {"cmake": {"define": {"SHARED": "ep"}}}
    body = (
        "[tool.scikit-build.cmake.define]\nFROM_PYPROJECT = '2'\nSHARED = 'pyproject'\n"
    )
    settings = make_reader(tmp_path, body, state="wheel").settings
    assert settings.cmake.define == {
        "FROM_DEFAULT": "1",
        "FROM_PYPROJECT": "2",
        "SHARED": "ep",  # override beats pyproject on key collision
    }


def test_multiple_providers_sorted_deterministically(tmp_path, providers):
    providers["override.b"] = lambda **_: {"cmake": {"build-type": "Debug"}}
    providers["override.a"] = lambda **_: {"cmake": {"build-type": "RelWithDebInfo"}}
    settings = make_reader(tmp_path, state="wheel").settings
    # Earlier entry-point name wins.
    assert settings.cmake.build_type == "RelWithDebInfo"


def test_provider_overrides_match_env(tmp_path, providers):
    def fedora(**_):
        return {
            "overrides": [
                {
                    "if": {"env": {"RPM_BUILD_ROOT": True}},
                    "cmake": {"build-type": "RelWithDebInfo"},
                    "install": {"strip": False},
                }
            ]
        }

    providers["default"] = fedora

    in_rpm = make_reader(
        tmp_path, state="wheel", env={"RPM_BUILD_ROOT": str(tmp_path)}
    ).settings
    assert in_rpm.cmake.build_type == "RelWithDebInfo"
    assert in_rpm.install.strip is False

    outside = make_reader(tmp_path, state="wheel", env={}).settings
    assert outside.cmake.build_type == "Release"


def test_opt_out_disables_providers(tmp_path, providers):
    providers["default"] = lambda **_: {"cmake": {"build-type": "RelWithDebInfo"}}
    settings = make_reader(
        tmp_path, state="wheel", env={"SKBUILD_NO_ENTRYPOINT_CONFIG": "1"}
    ).settings
    assert settings.cmake.build_type == "Release"


def test_unknown_level_warns_and_skips(tmp_path, providers, capsys):
    providers["bogus"] = lambda **_: {"cmake": {"build-type": "RelWithDebInfo"}}
    scikit_build_core._logging.rich_warning.cache_clear()
    settings = make_reader(tmp_path, state="wheel").settings
    assert settings.cmake.build_type == "Release"
    assert "must start with 'default' or 'override'" in capsys.readouterr().err


def test_minimum_version_stripped(tmp_path, providers):
    providers["default"] = lambda **_: {
        "minimum-version": "0.5",
        "cmake": {"build-type": "RelWithDebInfo"},
    }
    settings = make_reader(tmp_path, state="wheel").settings
    assert settings.minimum_version is None
    assert settings.cmake.build_type == "RelWithDebInfo"


def test_zero_arg_provider_supported(tmp_path, providers):
    def provider() -> dict[str, object]:
        return {"cmake": {"build-type": "RelWithDebInfo"}}

    providers["default"] = provider
    settings = make_reader(tmp_path, state="wheel").settings
    assert settings.cmake.build_type == "RelWithDebInfo"


def test_override_only_field_rejected(tmp_path, providers):
    # cmake.toolchain-file is an override_only field: hard-coding it in a static
    # source (including ep config) is rejected under strict_config.
    toolchain = str(tmp_path / "tc.cmake")
    providers["default"] = lambda **_: {"cmake": {"toolchain-file": toolchain}}
    reader = make_reader(tmp_path, state="wheel")
    with pytest.raises(SystemExit):
        reader.validate_may_exit()


def test_suggestions_name_entry_point_source(tmp_path, providers):
    providers["default"] = lambda **_: {"not-a-real-field": "x"}
    reader = make_reader(tmp_path, state="wheel")
    assert "entry-point config (default)" in reader._toml_src_names
    assert "not-a-real-field" in list(reader.unrecognized_options())
