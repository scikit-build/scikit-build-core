from __future__ import annotations

import sys
import sysconfig

import pytest

from scikit_build_core.builder.sysconfig import (
    get_abi_flags,
    get_cmake_platform,
    get_platform,
    get_soabi,
)


def test_get_platform_vscmd_arg_tgt_arch(monkeypatch):
    """VSCMD_ARG_TGT_ARCH should map to the corresponding Python platform name."""
    monkeypatch.setattr(sysconfig, "get_platform", lambda: "win-amd64")
    assert get_platform({"VSCMD_ARG_TGT_ARCH": "x86"}) == "win32"
    assert get_platform({"VSCMD_ARG_TGT_ARCH": "x64"}) == "win-amd64"
    assert get_platform({"VSCMD_ARG_TGT_ARCH": "arm64"}) == "win-arm64"


def test_get_platform_vscmd_unknown_arch(monkeypatch):
    """An unknown VSCMD_ARG_TGT_ARCH falls back to the host platform."""
    monkeypatch.setattr(sysconfig, "get_platform", lambda: "win-amd64")
    assert get_platform({"VSCMD_ARG_TGT_ARCH": "unknownarch"}) == "win-amd64"


def test_get_platform_setuptools_ext_suffix_arm64(monkeypatch):
    """arm64 in SETUPTOOLS_EXT_SUFFIX selects win-arm64."""
    monkeypatch.setattr(sysconfig, "get_platform", lambda: "win-amd64")
    assert (
        get_platform({"SETUPTOOLS_EXT_SUFFIX": ".cp312-win-arm64.pyd"}) == "win-arm64"
    )


def test_get_cmake_platform_mapped(monkeypatch):
    """get_cmake_platform converts Python platform names to CMake equivalents."""
    monkeypatch.setattr(sysconfig, "get_platform", lambda: "win-amd64")
    assert get_cmake_platform(None) == "x64"

    monkeypatch.setattr(sysconfig, "get_platform", lambda: "win32")
    assert get_cmake_platform(None) == "Win32"

    monkeypatch.setattr(sysconfig, "get_platform", lambda: "win-arm64")
    assert get_cmake_platform(None) == "ARM64"


def test_get_cmake_platform_passthrough(monkeypatch):
    """Platforms not in PLAT_TO_CMAKE are returned as-is."""
    monkeypatch.setattr(sysconfig, "get_platform", lambda: "linux-x86_64")
    assert get_cmake_platform(None) == "linux-x86_64"


def test_get_soabi_setuptools_ext_suffix():
    """SETUPTOOLS_EXT_SUFFIX overrides the detected SOABI."""
    env = {"SETUPTOOLS_EXT_SUFFIX": ".cpython-312-x86_64-linux-gnu.so"}
    result = get_soabi(env)
    assert result == "cpython-312-x86_64-linux-gnu"


def test_get_soabi_abi3_non_windows(monkeypatch):
    """abi3=True on a non-Windows platform returns 'abi3'."""
    monkeypatch.setattr(sysconfig, "get_platform", lambda: "linux-x86_64")
    assert get_soabi({}, abi3=True) == "abi3"


@pytest.mark.skipif(
    not sysconfig.get_platform().startswith("win"), reason="Windows only"
)
def test_get_soabi_abi3_windows():
    """abi3=True on Windows returns an empty string."""
    assert get_soabi({}, abi3=True) == ""


def test_get_abi_flags_returns_string():
    """get_abi_flags always returns a string."""
    result = get_abi_flags()
    assert isinstance(result, str)


@pytest.mark.skipif(
    sys.implementation.name != "cpython" or not sys.platform.startswith("win"),
    reason="CPython Windows only",
)
def test_get_abi_flags_windows_cpython():
    """On Windows CPython, abi flags are derived from packaging.tags."""
    result = get_abi_flags()
    assert isinstance(result, str)
