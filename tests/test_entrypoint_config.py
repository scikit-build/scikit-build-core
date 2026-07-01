"""
Tests for the ``scikit-build-core.config.default`` / ``.override`` entry-point
configuration providers.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest
from packaging.version import Version

from scikit_build_core._compat.importlib import metadata as compat_metadata
from scikit_build_core.settings import _load_entrypoint_config
from scikit_build_core.settings.skbuild_read_settings import SettingsReader

if TYPE_CHECKING:
    from collections.abc import Callable
    from pathlib import Path


class FakeEntryPoint:
    """Minimal stand-in for ``importlib.metadata.EntryPoint``."""

    def __init__(self, name: str, func: object) -> None:
        self.name = name
        self._func = func

    def load(self) -> object:
        return self._func


@pytest.fixture
def register(monkeypatch):
    """Register fake entry-point config providers.

    Call ``register(level, name, func)`` with ``level`` of "default" or
    "override" and an arbitrary ``name``.
    """
    groups: dict[str, dict[str, object]] = {
        _load_entrypoint_config.GROUP_DEFAULT: {},
        _load_entrypoint_config.GROUP_OVERRIDE: {},
    }

    def fake_entry_points(*, group: str):
        return [
            FakeEntryPoint(name, func) for name, func in groups.get(group, {}).items()
        ]

    # The loader resolves entry points through this shared compat module.
    monkeypatch.setattr(compat_metadata, "entry_points", fake_entry_points)

    def add(level: str, name: str, func: Callable[..., object]) -> None:
        group = (
            _load_entrypoint_config.GROUP_OVERRIDE
            if level == "override"
            else _load_entrypoint_config.GROUP_DEFAULT
        )
        groups[group][name] = func

    return add


def make_reader(tmp_path: Path, body: str = "", **kwargs) -> SettingsReader:
    pyproject_toml = tmp_path / "pyproject.toml"
    pyproject_toml.write_text(body, encoding="utf-8")
    return SettingsReader.from_file(pyproject_toml, {}, **kwargs)


def test_default_provider_applies_when_silent(tmp_path, register):
    register(
        "default",
        "distro",
        lambda **_: {
            "cmake": {"build-type": "RelWithDebInfo"},
            "install": {"strip": False},
        },
    )
    settings = make_reader(tmp_path, state="wheel").settings
    assert settings.cmake.build_type == "RelWithDebInfo"
    assert settings.install.strip is False


def test_default_provider_loses_to_pyproject(tmp_path, register):
    register(
        "default", "distro", lambda **_: {"cmake": {"build-type": "RelWithDebInfo"}}
    )
    body = "[tool.scikit-build.cmake]\nbuild-type = 'Debug'\n"
    settings = make_reader(tmp_path, body, state="wheel").settings
    assert settings.cmake.build_type == "Debug"


def test_override_provider_beats_pyproject(tmp_path, register):
    register(
        "override", "distro", lambda **_: {"cmake": {"build-type": "RelWithDebInfo"}}
    )
    body = "[tool.scikit-build.cmake]\nbuild-type = 'Debug'\n"
    settings = make_reader(tmp_path, body, state="wheel").settings
    assert settings.cmake.build_type == "RelWithDebInfo"


def test_override_still_beaten_by_config_settings(tmp_path, register):
    register(
        "override", "distro", lambda **_: {"cmake": {"build-type": "RelWithDebInfo"}}
    )
    pyproject_toml = tmp_path / "pyproject.toml"
    pyproject_toml.write_text("", encoding="utf-8")
    reader = SettingsReader.from_file(
        pyproject_toml, {"cmake.build-type": "Release"}, state="wheel"
    )
    assert reader.settings.cmake.build_type == "Release"


def test_dict_fields_merge_across_levels(tmp_path, register):
    register(
        "default", "distro", lambda **_: {"cmake": {"define": {"FROM_DEFAULT": "1"}}}
    )
    register("override", "distro", lambda **_: {"cmake": {"define": {"SHARED": "ep"}}})
    body = (
        "[tool.scikit-build.cmake.define]\nFROM_PYPROJECT = '2'\nSHARED = 'pyproject'\n"
    )
    settings = make_reader(tmp_path, body, state="wheel").settings
    assert settings.cmake.define == {
        "FROM_DEFAULT": "1",
        "FROM_PYPROJECT": "2",
        "SHARED": "ep",  # override beats pyproject on key collision
    }


def test_multiple_providers_sorted_deterministically(tmp_path, register):
    # Arbitrary names; the alphabetically-first one wins.
    register("override", "zzz", lambda **_: {"cmake": {"build-type": "Debug"}})
    register("override", "aaa", lambda **_: {"cmake": {"build-type": "RelWithDebInfo"}})
    settings = make_reader(tmp_path, state="wheel").settings
    assert settings.cmake.build_type == "RelWithDebInfo"


def test_provider_overrides_match_env(tmp_path, register):
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

    register("default", "fedora", fedora)

    in_rpm = make_reader(
        tmp_path, state="wheel", env={"RPM_BUILD_ROOT": str(tmp_path)}
    ).settings
    assert in_rpm.cmake.build_type == "RelWithDebInfo"
    assert in_rpm.install.strip is False

    outside = make_reader(tmp_path, state="wheel", env={}).settings
    assert outside.cmake.build_type == "Release"


def test_opt_out_disables_providers(tmp_path, register):
    register(
        "default", "distro", lambda **_: {"cmake": {"build-type": "RelWithDebInfo"}}
    )
    settings = make_reader(
        tmp_path, state="wheel", env={"SKBUILD_NO_ENTRYPOINT_CONFIG": "1"}
    ).settings
    assert settings.cmake.build_type == "Release"


def test_minimum_version_applies(tmp_path, register):
    register(
        "default",
        "distro",
        lambda **_: {
            "minimum-version": "0.5",
            "cmake": {"build-type": "RelWithDebInfo"},
        },
    )
    settings = make_reader(tmp_path, state="wheel").settings
    assert settings.minimum_version == Version("0.5")
    assert settings.cmake.build_type == "RelWithDebInfo"


def test_minimum_version_applies_via_override(tmp_path, register):
    # A provider may also set minimum-version inside an overrides block.
    register(
        "default",
        "distro",
        lambda **_: {
            "overrides": [{"if": {"env": {"SET_MIN": True}}, "minimum-version": "0.5"}]
        },
    )
    settings = make_reader(tmp_path, state="wheel", env={"SET_MIN": "1"}).settings
    assert settings.minimum_version == Version("0.5")


def test_zero_arg_provider_supported(tmp_path, register):
    def provider() -> dict[str, object]:
        return {"cmake": {"build-type": "RelWithDebInfo"}}

    register("default", "distro", provider)
    settings = make_reader(tmp_path, state="wheel").settings
    assert settings.cmake.build_type == "RelWithDebInfo"


def test_override_only_field_rejected(tmp_path, register):
    # cmake.toolchain-file is an override_only field: hard-coding it in a static
    # source (including ep config) is rejected under strict_config.
    toolchain = str(tmp_path / "tc.cmake")
    register("default", "distro", lambda **_: {"cmake": {"toolchain-file": toolchain}})
    reader = make_reader(tmp_path, state="wheel")
    with pytest.raises(SystemExit):
        reader.validate_may_exit()


def test_suggestions_name_entry_point_source(tmp_path, register):
    register("default", "distro", lambda **_: {"not-a-real-field": "x"})
    reader = make_reader(tmp_path, state="wheel")
    assert "entry-point config (distro)" in reader._toml_src_names
    assert "not-a-real-field" in list(reader.unrecognized_options())
