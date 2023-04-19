import os
import platform
import pprint
import sys
import sysconfig
import typing
from pathlib import Path
from types import SimpleNamespace

import pytest

from scikit_build_core.builder.builder import Builder, archs_to_tags, get_archs
from scikit_build_core.builder.macos import get_macosx_deployment_target
from scikit_build_core.builder.sysconfig import (
    get_python_include_dir,
    get_python_library,
)
from scikit_build_core.builder.wheel_tag import WheelTag
from scikit_build_core.cmake import CMaker
from scikit_build_core.settings.skbuild_model import ScikitBuildSettings, WheelSettings


# The envvar_higher case shouldn't happen, but the compiler should cause the
# correct failure
@pytest.mark.parametrize(
    ("pycom", "envvar", "answer"),
    [
        pytest.param("12.5.2", None, "12.0", id="only_plat_round"),
        pytest.param("10.12.2", None, "10.12", id="only_plat_classic"),
        pytest.param("10.12.2", "10.11", "10.11", id="env_var_lower"),
        pytest.param("10.12.2", "10.13", "10.13", id="env_var_higher"),
        pytest.param("11.2.12", "11.2", "11.0", id="same_vars_round"),
        pytest.param("12.1.2", "11", "11.0", id="env_var_no_dot"),
        pytest.param("11.2.12", "random", "11.0", id="invalid_env_var"),
        pytest.param("11.2.12", "rand.om", "11.0", id="invalid_env_var_with_dot"),
    ],
)
def test_macos_version(monkeypatch, pycom, envvar, answer):
    monkeypatch.setattr(platform, "mac_ver", lambda: (pycom, "", ""))
    if envvar is None:
        monkeypatch.delenv("MACOSX_DEPLOYMENT_TARGET", raising=False)
    else:
        monkeypatch.setenv("MACOSX_DEPLOYMENT_TARGET", envvar)

    assert str(get_macosx_deployment_target(arm=False)) == answer


def test_get_python_include_dir():
    assert get_python_include_dir().is_dir()


@pytest.mark.xfail(
    strict=False, reason="Doesn't matter if this fails, usually not used"
)
def test_get_python_library():
    pprint.pprint(sysconfig.get_config_vars())

    lib = get_python_library({})
    if sysconfig.get_platform().startswith("win"):
        assert lib
        assert lib.is_file()
    else:
        assert lib is None


@pytest.mark.skipif(not sysconfig.get_platform().startswith("win"), reason="MSVC only")
def test_get_python_library_xcompile(tmp_path):
    config_path = tmp_path / "tmp.cfg"
    config_path.write_text(
        """\
[build_ext]
library_dirs=C:\\Python\\libs
    """
    )
    env = {"DIST_EXTRA_CONFIG": str(config_path)}
    lib = get_python_library(env)
    assert lib
    assert lib.parent == Path("C:\\Python\\libs")
    assert lib.parent != Path("C:\\Python\\libs\\python3.lib")

    lib2 = get_python_library(env, abi3=True)
    assert lib2
    assert lib2 == Path("C:\\Python\\libs\\python3.lib")


@pytest.mark.parametrize("archs", [["x86_64"], ["arm64", "universal2"]])
def test_builder_macos_arch(monkeypatch, archs):
    archflags = " ".join(f"-arch {arch}" for arch in archs)
    monkeypatch.setattr(sys, "platform", "darwin")
    assert get_archs({"ARCHFLAGS": archflags}) == archs


def test_builder_macos_arch_extra(monkeypatch):
    archflags = "-arch arm64 -arch x86_64"
    monkeypatch.setattr(sys, "platform", "darwin")
    monkeypatch.setenv("ARCHFLAGS", archflags)
    tmpcfg = typing.cast(CMaker, SimpleNamespace(env=os.environ.copy()))

    tmpbuilder = Builder(
        settings=ScikitBuildSettings(wheel=WheelSettings()),
        config=tmpcfg,
    )
    assert archs_to_tags(get_archs(tmpbuilder.config.env)) == ["universal2"]


@pytest.mark.parametrize(
    ("minver", "archs", "answer"),
    [
        pytest.param("10.12", ["x86_64"], "macosx_10_12_x86_64", id="10.12_x86_64"),
        pytest.param("10.12", ["arm64"], "macosx_11_0_arm64", id="10.12_arm64"),
        pytest.param(
            "10.12", ["universal2"], "macosx_10_12_universal2", id="10.12_universal2"
        ),
    ],
)
def test_wheel_tag(monkeypatch, minver, archs, answer):
    monkeypatch.setattr(sys, "platform", "darwin")
    monkeypatch.setenv("MACOSX_DEPLOYMENT_TARGET", minver)
    monkeypatch.setattr(platform, "mac_ver", lambda: ("10.9.2", "", ""))

    tags = WheelTag.compute_best(archs)
    plat = str(tags).split("-")[-1]
    assert plat == answer


def test_wheel_tag_expand(monkeypatch):
    monkeypatch.setattr(sys, "platform", "darwin")
    monkeypatch.setenv("MACOSX_DEPLOYMENT_TARGET", "10.10")
    monkeypatch.setattr(platform, "mac_ver", lambda: ("10.9.2", "", ""))

    tags = WheelTag.compute_best(["universal2"])
    plat = str(tags).split("-")[-1]
    assert plat == "macosx_10_10_universal2"

    tags = WheelTag.compute_best(["universal2"], expand_macos=True)
    plat = str(tags).split("-")[-1]
    assert (
        plat
        == "macosx_10_10_universal2.macosx_11_0_universal2.macosx_10_10_x86_64.macosx_11_0_arm64"
    )


def test_wheel_tag_expand_11(monkeypatch):
    monkeypatch.setattr(sys, "platform", "darwin")
    monkeypatch.setenv("MACOSX_DEPLOYMENT_TARGET", "11.2")
    monkeypatch.setattr(platform, "mac_ver", lambda: ("10.9.2", "", ""))

    tags = WheelTag.compute_best(["universal2"])
    plat = str(tags).split("-")[-1]
    assert plat == "macosx_11_0_universal2"

    tags = WheelTag.compute_best(["universal2"], expand_macos=True)
    plat = str(tags).split("-")[-1]
    assert plat == "macosx_11_0_universal2.macosx_11_0_x86_64.macosx_11_0_arm64"


def test_wheel_tag_with_abi_darwin(monkeypatch):
    monkeypatch.setattr(sys, "platform", "darwin")
    monkeypatch.setenv("MACOSX_DEPLOYMENT_TARGET", "10.10")
    monkeypatch.setattr(platform, "mac_ver", lambda: ("10.9.2", "", ""))

    tags = WheelTag.compute_best(["x86_64"], py_api="cp39")
    if sys.version_info < (3, 9) or sys.implementation.name != "cpython":
        assert "macosx_10_10_x86_64" in str(tags)
        assert "abi3" not in str(tags)
        assert "cp39" not in str(tags)
    else:
        assert str(tags) == "cp39-abi3-macosx_10_10_x86_64"

    tags = WheelTag.compute_best(["x86_64"], py_api="cp37")
    if sys.implementation.name != "cpython":
        assert "macosx_10_10_x86_64" in str(tags)
        assert "abi3" not in str(tags)
        assert "cp37" not in str(tags)
    else:
        assert str(tags) == "cp37-abi3-macosx_10_10_x86_64"

    tags = WheelTag.compute_best(["x86_64"], py_api="py3")
    assert str(tags) == "py3-none-macosx_10_10_x86_64"

    tags = WheelTag.compute_best(["x86_64"], py_api="py2.py3")
    assert str(tags) == "py2.py3-none-macosx_10_10_x86_64"
