from __future__ import annotations

import os
import platform
import pprint
import sys
import sysconfig
import typing
import unittest.mock
from pathlib import Path
from types import SimpleNamespace

import pytest
from packaging.version import Version

from scikit_build_core.builder.builder import (
    Builder,
    _sanitize_path,
    archs_to_tags,
    get_archs,
)
from scikit_build_core.builder.macos import get_macosx_deployment_target
from scikit_build_core.builder.sysconfig import (
    _config_var_is_set,
    _windows_lib_names,
    get_python_include_dir,
    get_python_library,
)
from scikit_build_core.builder.wheel_tag import WheelTag
from scikit_build_core.cmake import CMake, CMaker
from scikit_build_core.settings.skbuild_model import (
    BuildSettings,
    CMakeSettings,
    CMakeSettingsDefine,
    EnvValue,
    ScikitBuildSettings,
    SearchSettings,
    WheelSettings,
)


class VersionInfo:
    """Minimal sys.version_info replacement for monkeypatching in tests."""

    def __init__(
        self,
        major: int,
        minor: int,
        micro: int = 0,
        releaselevel: str = "final",
        serial: int = 0,
    ) -> None:
        self.major = major
        self.minor = minor
        self.micro = micro
        self.releaselevel = releaselevel
        self.serial = serial

    @classmethod
    def from_str(cls, version: str) -> VersionInfo:
        major, minor, *rest = (int(x) for x in version.split("."))
        micro = rest[0] if rest else 0
        return cls(major, minor, micro)

    def __getitem__(self, index: int) -> int | str:
        return (self.major, self.minor, self.micro, self.releaselevel, self.serial)[
            index
        ]

    def __ge__(self, other: tuple[int, ...]) -> bool:
        return (self.major, self.minor, self.micro) >= other[:3]


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


@pytest.mark.parametrize(
    ("envvar", "defines", "args", "answer"),
    [
        pytest.param(
            None,
            {"CMAKE_OSX_DEPLOYMENT_TARGET": "11.0"},
            (),
            "11.0",
            id="define_only",
        ),
        pytest.param(
            None,
            {},
            ("-DCMAKE_OSX_DEPLOYMENT_TARGET=10.13",),
            "10.13",
            id="arg_only",
        ),
        pytest.param(
            None,
            {},
            ("-DCMAKE_OSX_DEPLOYMENT_TARGET:STRING=10.13",),
            "10.13",
            id="arg_typed",
        ),
        # cmake.define / cmake.args win over the env var fallback.
        pytest.param(
            "12.0",
            {"CMAKE_OSX_DEPLOYMENT_TARGET": "11.0"},
            (),
            "11.0",
            id="define_beats_envvar",
        ),
        # args win over the define, mirroring CMake's command-line precedence.
        pytest.param(
            None,
            {"CMAKE_OSX_DEPLOYMENT_TARGET": "11.0"},
            ("-DCMAKE_OSX_DEPLOYMENT_TARGET=10.13",),
            "10.13",
            id="arg_beats_define",
        ),
        # An unreadable cmake value falls back to the env var.
        pytest.param(
            "12.0",
            {"CMAKE_OSX_DEPLOYMENT_TARGET": "random"},
            (),
            "12.0",
            id="invalid_define_falls_back_to_envvar",
        ),
    ],
)
def test_macos_version_cmake_osx_deployment_target(
    monkeypatch, envvar, defines, args, answer
):
    # Pin the platform version high so the answer must come from the explicit
    # cmake setting (or env var fallback), not the current macOS version.
    monkeypatch.setattr(platform, "mac_ver", lambda: ("15.0.0", "", ""))
    if envvar is None:
        monkeypatch.delenv("MACOSX_DEPLOYMENT_TARGET", raising=False)
    else:
        monkeypatch.setenv("MACOSX_DEPLOYMENT_TARGET", envvar)

    result = get_macosx_deployment_target(
        arm=False,
        cmake_defines={k: CMakeSettingsDefine(v) for k, v in defines.items()},
        cmake_args=args,
    )
    assert str(result) == answer


def test_get_python_include_dir():
    assert get_python_include_dir().is_dir()


def test_get_python_library():
    pprint.pprint(
        {
            k: v
            for k, v in sysconfig.get_config_vars().items()
            if isinstance(v, str) and 128 > len(v) > 2 and not k.startswith("MODULE")
        }
    )

    lib = get_python_library({})
    if sysconfig.get_platform().startswith("win"):
        # Recompute the expected name independently of the implementation.
        free_threaded = _config_var_is_set("Py_GIL_DISABLED")
        debug = _config_var_is_set("Py_DEBUG")
        t = "t" if free_threaded else ""
        d = "_d" if debug else ""
        expected = f"python3{sys.version_info[1]}{t}{d}.lib"
        assert lib is not None
        assert lib.is_file()
        assert lib.name == expected
        assert lib.parent.name in {"libs", "lib"}

        # The stable ABI is CPython-only; PyPy ships no python3[t].lib.
        if sys.implementation.name == "cpython":
            abi3_lib = get_python_library({}, abi3=True)
            assert abi3_lib is not None
            assert abi3_lib.name == f"python3{d}.lib"

            abi3t_lib = get_python_library({}, abi3t=True)
            assert abi3t_lib is not None
            assert abi3t_lib.name == f"python3{t}{d}.lib"
    else:
        # POSIX usually returns None (FindPython resolves it itself); if a real
        # library does resolve, it must be an existing file.
        assert lib is None or lib.is_file()


@pytest.mark.parametrize("free_threaded", [False, True])
@pytest.mark.parametrize("debug", [False, True])
@pytest.mark.parametrize("variant", ["classic", "abi3", "abi3t"])
def test_windows_lib_names(monkeypatch, variant, debug, free_threaded):
    overrides = {
        "Py_GIL_DISABLED": "1" if free_threaded else None,
        "Py_DEBUG": 1 if debug else 0,
    }
    real = sysconfig.get_config_var
    monkeypatch.setattr(
        sysconfig,
        "get_config_var",
        lambda name: overrides[name] if name in overrides else real(name),
    )

    abi3 = variant == "abi3"
    abi3t = variant == "abi3t"
    names = _windows_lib_names(abi3=abi3, abi3t=abi3t)

    t = "t" if free_threaded else ""
    if abi3:
        # Classic stable ABI has no free-threaded variant.
        base = "python3"
    elif abi3t:
        base = f"python3{t}"
    else:
        base = f"python3{sys.version_info[1]}{t}"

    expected = [f"{base}.lib"]
    if debug:
        expected.insert(0, f"{base}_d.lib")
    assert names == expected


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

    lib3 = get_python_library(env, abi3t=True)
    assert lib3
    assert lib3 == Path("C:\\Python\\libs\\python3t.lib")


@pytest.mark.parametrize("archs", [["x86_64"], ["arm64", "universal2"]])
def test_builder_macos_arch(monkeypatch, archs):
    archflags = " ".join(f"-arch {arch}" for arch in archs)
    monkeypatch.setattr(sys, "platform", "darwin")
    assert get_archs({"ARCHFLAGS": archflags}) == archs


def test_builder_macos_arch_cmake_system_processor(monkeypatch):
    # If CMAKE_SYSTEM_PROCESSOR is in the cmake args, ARCHFLAGS is ignored (#207).
    monkeypatch.setattr(sys, "platform", "darwin")
    env = {"ARCHFLAGS": "-arch x86_64"}
    cmake_args = ["-DCMAKE_SYSTEM_PROCESSOR=arm64"]
    assert get_archs(env, cmake_args) == ["arm64"]
    # Without the cmake arg, ARCHFLAGS wins.
    assert get_archs(env) == ["x86_64"]


def test_builder_macos_arch_extra(monkeypatch):
    archflags = "-arch arm64 -arch x86_64"
    monkeypatch.setattr(sys, "platform", "darwin")
    monkeypatch.setenv("ARCHFLAGS", archflags)
    tmpcfg = typing.cast("CMaker", SimpleNamespace(env=os.environ.copy()))

    tmpbuilder = Builder(
        settings=ScikitBuildSettings(wheel=WheelSettings()),
        config=tmpcfg,
    )
    assert archs_to_tags(get_archs(tmpbuilder.config.env)) == ["universal2"]


@pytest.mark.parametrize(
    ("cmake_args", "answer"),
    [
        ("-DA=1 -DB=2", ["-DA=1", "-DB=2"]),
        (r"-DA='1 1' -DB=\'2\'", ["-DA=1 1", "-DB='2'"]),
        (r'-DA="1 1" -DB=\"2\"', ["-DA=1 1", '-DB="2"']),
        ('"-DA=1 1" -DB=2', ["-DA=1 1", "-DB=2"]),
    ],
)
def test_builder_get_cmake_args(monkeypatch, cmake_args, answer):
    monkeypatch.setenv("CMAKE_ARGS", cmake_args)
    tmpcfg = typing.cast("CMaker", SimpleNamespace(env=os.environ.copy()))
    tmpbuilder = Builder(
        settings=ScikitBuildSettings(wheel=WheelSettings()),
        config=tmpcfg,
    )
    assert tmpbuilder.get_cmake_args() == answer


def test_builder_exports_source_date_epoch(monkeypatch):
    monkeypatch.delenv("SOURCE_DATE_EPOCH", raising=False)
    tmpcfg = typing.cast("CMaker", SimpleNamespace(env=os.environ.copy()))
    builder = Builder(
        settings=ScikitBuildSettings(wheel=WheelSettings(reproducible=True)),
        config=tmpcfg,
    )
    assert builder.config.env["SOURCE_DATE_EPOCH"] == "1667997441"


def test_builder_keeps_existing_source_date_epoch(monkeypatch):
    monkeypatch.setenv("SOURCE_DATE_EPOCH", "1234567890")
    tmpcfg = typing.cast("CMaker", SimpleNamespace(env=os.environ.copy()))
    builder = Builder(
        settings=ScikitBuildSettings(wheel=WheelSettings(reproducible=True)),
        config=tmpcfg,
    )
    assert builder.config.env["SOURCE_DATE_EPOCH"] == "1234567890"


def test_builder_env_table_wins_over_source_date_epoch(monkeypatch):
    monkeypatch.delenv("SOURCE_DATE_EPOCH", raising=False)
    tmpcfg = typing.cast("CMaker", SimpleNamespace(env=os.environ.copy()))
    builder = Builder(
        settings=ScikitBuildSettings(
            wheel=WheelSettings(reproducible=True),
            env={"SOURCE_DATE_EPOCH": EnvValue("42")},
        ),
        config=tmpcfg,
    )
    assert builder.config.env["SOURCE_DATE_EPOCH"] == "42"


def test_builder_no_source_date_epoch_when_not_reproducible(monkeypatch):
    monkeypatch.delenv("SOURCE_DATE_EPOCH", raising=False)
    tmpcfg = typing.cast("CMaker", SimpleNamespace(env=os.environ.copy()))
    builder = Builder(
        settings=ScikitBuildSettings(wheel=WheelSettings(reproducible=False)),
        config=tmpcfg,
    )
    assert "SOURCE_DATE_EPOCH" not in builder.config.env


def test_build_tool_args():
    config = unittest.mock.create_autospec(CMaker)
    config.env = {}
    settings = ScikitBuildSettings(build=BuildSettings(tool_args=["b"]))
    tmpbuilder = Builder(
        settings=settings,
        config=typing.cast("CMaker", config),
    )
    tmpbuilder.build(["a"])
    config.build.assert_called_once_with(
        build_args=["a", "--", "b"],
        targets=[],
        verbose=settings.build.verbose,
        build_type=None,
    )


def configure_builder_with_limited_api(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    *,
    limited_api: bool | None,
    py_api: str = "",
) -> str:
    source_dir = tmp_path / "src"
    source_dir.mkdir()

    config = CMaker(
        CMake(Version("3.30"), Path("cmake")),
        source_dir=source_dir,
        build_dir=tmp_path / "build",
        build_type="Release",
    )
    monkeypatch.setattr(config, "configure", unittest.mock.Mock())

    builder = Builder(
        settings=ScikitBuildSettings(
            search=SearchSettings(site_packages=False),
            wheel=WheelSettings(py_api=py_api),
        ),
        config=config,
    )
    monkeypatch.setattr(Builder, "_get_entry_point_search_path", lambda *_: {})

    builder.configure(defines={}, limited_api=limited_api)
    return config.init_cache_file.read_text(encoding="utf-8")


def patch_cpython_runtime(monkeypatch: pytest.MonkeyPatch) -> None:
    implementation = vars(sys.implementation).copy()
    implementation["name"] = "cpython"
    monkeypatch.setattr(
        sys,
        "implementation",
        SimpleNamespace(**implementation),
    )


def test_builder_limited_api_override_classic(tmp_path, monkeypatch):
    get_config_var = sysconfig.get_config_var
    monkeypatch.setattr(
        sysconfig,
        "get_config_var",
        lambda x: None if x == "Py_GIL_DISABLED" else get_config_var(x),
    )
    patch_cpython_runtime(monkeypatch)

    cache = configure_builder_with_limited_api(tmp_path, monkeypatch, limited_api=True)

    expected_soabi = "" if sysconfig.get_platform().startswith("win") else "abi3"
    assert "Development.SABIModule" in cache
    assert f"set(SKBUILD_SOABI [===[{expected_soabi}]===] CACHE STRING" in cache
    assert "Py_TARGET_ABI3T" not in cache


def test_builder_limited_api_override_free_threaded(tmp_path, monkeypatch):
    get_config_var = sysconfig.get_config_var
    monkeypatch.setattr(
        sysconfig,
        "get_config_var",
        lambda x: "t" if x == "Py_GIL_DISABLED" else get_config_var(x),
    )
    patch_cpython_runtime(monkeypatch)

    cache = configure_builder_with_limited_api(tmp_path, monkeypatch, limited_api=True)

    expected_soabi = "" if sysconfig.get_platform().startswith("win") else "abi3t"
    assert "Development.SABIModule" in cache
    assert f"set(SKBUILD_SOABI [===[{expected_soabi}]===] CACHE STRING" in cache
    assert "set(Py_TARGET_ABI3T [===[1]===] CACHE STRING" in cache


def test_builder_limited_api_auto_free_threaded(tmp_path, monkeypatch):
    get_config_var = sysconfig.get_config_var
    monkeypatch.setattr(
        sysconfig,
        "get_config_var",
        lambda x: "t" if x == "Py_GIL_DISABLED" else get_config_var(x),
    )
    patch_cpython_runtime(monkeypatch)
    monkeypatch.setattr(sys, "version_info", VersionInfo(3, 15))

    cache = configure_builder_with_limited_api(
        tmp_path, monkeypatch, limited_api=None, py_api="cp315t"
    )

    expected_soabi = "" if sysconfig.get_platform().startswith("win") else "abi3t"
    assert "Development.SABIModule" in cache
    assert f"set(SKBUILD_SOABI [===[{expected_soabi}]===] CACHE STRING" in cache
    assert "set(Py_TARGET_ABI3T [===[1]===] CACHE STRING" in cache


@pytest.mark.parametrize(
    ("gil", "soabi", "is_ft"),
    [("t", "abi3t", True), (None, "abi3", False)],
    ids=["free_threaded", "gil"],
)
def test_builder_combined_abi3_abi3t(tmp_path, monkeypatch, gil, soabi, is_ft):
    """Combined py-api builds the one binary matching the current interpreter."""
    get_config_var = sysconfig.get_config_var
    monkeypatch.setattr(
        sysconfig,
        "get_config_var",
        lambda x: gil if x == "Py_GIL_DISABLED" else get_config_var(x),
    )
    patch_cpython_runtime(monkeypatch)
    monkeypatch.setattr(sys, "version_info", VersionInfo(3, 15))

    cache = configure_builder_with_limited_api(
        tmp_path, monkeypatch, limited_api=None, py_api="cp315.cp315t"
    )

    expected_soabi = "" if sysconfig.get_platform().startswith("win") else soabi
    assert "Development.SABIModule" in cache
    assert f"set(SKBUILD_SOABI [===[{expected_soabi}]===] CACHE STRING" in cache
    assert "set(SKBUILD_SABI_VERSION [===[3.15]===] CACHE STRING" in cache
    assert ("Py_TARGET_ABI3T" in cache) == is_ft


def configure_builder_with_version(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    version: Version,
) -> str:
    source_dir = tmp_path / "src"
    source_dir.mkdir()

    config = CMaker(
        CMake(Version("3.30"), Path("cmake")),
        source_dir=source_dir,
        build_dir=tmp_path / "build",
        build_type="Release",
    )
    monkeypatch.setattr(config, "configure", unittest.mock.Mock())

    builder = Builder(
        settings=ScikitBuildSettings(search=SearchSettings(site_packages=False)),
        config=config,
    )
    monkeypatch.setattr(Builder, "_get_entry_point_search_path", lambda *_: {})

    builder.configure(defines={}, name="example", version=version)
    return config.init_cache_file.read_text(encoding="utf-8")


@pytest.mark.parametrize(
    ("version", "full", "capped"),
    [
        ("1.2.3", "1.2.3", "1.2.3"),
        ("1.2", "1.2", "1.2"),
        ("2", "2", "2"),
        ("1.2.3.4", "1.2.3.4", "1.2.3.4"),
        ("1.2.3.4.5", "1.2.3.4.5", "1.2.3.4"),
        ("1!2.3.4", "1!2.3.4", "2.3.4"),
        ("1.0.0a1", "1.0.0a1", "1.0.0"),
        ("1.2.3.dev4+local", "1.2.3.dev4+local", "1.2.3"),
    ],
)
def test_builder_project_version_cmake(tmp_path, monkeypatch, version, full, capped):
    cache = configure_builder_with_version(tmp_path, monkeypatch, Version(version))
    assert f"set(SKBUILD_PROJECT_VERSION [===[{capped}]===] CACHE STRING" in cache
    assert f"set(SKBUILD_PROJECT_VERSION_FULL [===[{full}]===] CACHE STRING" in cache


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
    get_config_var = sysconfig.get_config_var
    monkeypatch.setattr(
        sysconfig,
        "get_config_var",
        lambda x: None if x == "Py_GIL_DISABLED" else get_config_var(x),
    )
    monkeypatch.setattr(sys, "platform", "darwin")
    monkeypatch.setenv("MACOSX_DEPLOYMENT_TARGET", minver)
    monkeypatch.setattr(platform, "mac_ver", lambda: ("10.9.2", "", ""))

    tags = WheelTag.compute_best(archs)
    plat = str(tags).split("-")[-1]
    assert plat == answer


@pytest.mark.parametrize("archs", ["x86_64", "arm64", "universal2"])
def test_wheel_build_tag(monkeypatch, archs):
    get_config_var = sysconfig.get_config_var
    monkeypatch.setattr(
        sysconfig,
        "get_config_var",
        lambda x: None if x == "Py_GIL_DISABLED" else get_config_var(x),
    )
    monkeypatch.setattr(sys, "platform", "darwin")
    monkeypatch.setenv("MACOSX_DEPLOYMENT_TARGET", "10.12")
    monkeypatch.setattr(platform, "mac_ver", lambda: ("10.9.2", "", ""))

    tags = WheelTag.compute_best(archs, build_tag="1")
    answer = str(tags).split("-")[0]
    assert answer == "1"


def test_wheel_tag_expand(monkeypatch):
    get_config_var = sysconfig.get_config_var
    monkeypatch.setattr(
        sysconfig,
        "get_config_var",
        lambda x: None if x == "Py_GIL_DISABLED" else get_config_var(x),
    )
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
    get_config_var = sysconfig.get_config_var
    monkeypatch.setattr(
        sysconfig,
        "get_config_var",
        lambda x: None if x == "Py_GIL_DISABLED" else get_config_var(x),
    )
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
    get_config_var = sysconfig.get_config_var
    monkeypatch.setattr(
        sysconfig,
        "get_config_var",
        lambda x: None if x == "Py_GIL_DISABLED" else get_config_var(x),
    )
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

    tags = WheelTag.compute_best(["x86_64"], py_api="cp38")
    if sys.implementation.name != "cpython":
        assert "macosx_10_10_x86_64" in str(tags)
        assert "abi3" not in str(tags)
        assert "cp38" not in str(tags)
    else:
        assert str(tags) == "cp38-abi3-macosx_10_10_x86_64"

    tags = WheelTag.compute_best(["x86_64"], py_api="py3")
    assert str(tags) == "py3-none-macosx_10_10_x86_64"

    tags = WheelTag.compute_best(["x86_64"], py_api="py2.py3")
    assert str(tags) == "py2.py3-none-macosx_10_10_x86_64"


def test_wheel_tag_with_abi3t_darwin(monkeypatch):
    """Test cp315t free-threaded stable ABI tag."""
    get_config_var = sysconfig.get_config_var
    monkeypatch.setattr(
        sysconfig,
        "get_config_var",
        lambda x: "t" if x == "Py_GIL_DISABLED" else get_config_var(x),
    )
    monkeypatch.setattr(sys, "platform", "darwin")
    monkeypatch.setattr(sys, "implementation", SimpleNamespace(name="cpython"))
    monkeypatch.setenv("MACOSX_DEPLOYMENT_TARGET", "10.10")
    monkeypatch.setattr(platform, "mac_ver", lambda: ("10.9.2", "", ""))

    monkeypatch.setattr(sys, "version_info", VersionInfo(3, 15))

    tags = WheelTag.compute_best(["x86_64"], py_api="cp315t")
    assert str(tags) == "cp315-abi3t-macosx_10_10_x86_64"

    tags = WheelTag.compute_best(["x86_64"], py_api="cp316t")
    assert "abi3t" not in str(tags)
    assert "cp316t" not in str(tags)


def test_wheel_tag_with_combined_abi3_abi3t_free_threaded(monkeypatch):
    """On a free-threaded build, cp315.cp315t broadens the abi3t tag to abi3.abi3t.

    abi3t is a subset of abi3 (PEP 803), so the single free-threaded binary
    also loads under a GIL-enabled CPython, justifying the combined tag.
    """
    get_config_var = sysconfig.get_config_var
    monkeypatch.setattr(
        sysconfig,
        "get_config_var",
        lambda x: "t" if x == "Py_GIL_DISABLED" else get_config_var(x),
    )
    monkeypatch.setattr(sys, "platform", "darwin")
    monkeypatch.setattr(sys, "implementation", SimpleNamespace(name="cpython"))
    monkeypatch.setenv("MACOSX_DEPLOYMENT_TARGET", "10.10")
    monkeypatch.setattr(platform, "mac_ver", lambda: ("10.9.2", "", ""))
    monkeypatch.setattr(sys, "version_info", VersionInfo(3, 15))

    tags = WheelTag.compute_best(["x86_64"], py_api="cp315.cp315t")
    assert str(tags) == "cp315-abi3.abi3t-macosx_10_10_x86_64"
    assert {str(t) for t in tags.as_tags_set()} == {
        "cp315-abi3-macosx_10_10_x86_64",
        "cp315-abi3t-macosx_10_10_x86_64",
    }

    # Too-high combined request falls back to the default interpreter tag
    tags = WheelTag.compute_best(["x86_64"], py_api="cp316.cp316t")
    assert "abi3" not in str(tags)


def test_wheel_tag_combined_rejects_higher_classic_minor(monkeypatch):
    """A combined abi3.abi3t tag shares one minor, so the classic abi3 request
    must not be newer than the free-threaded one. cp316.cp315t would otherwise
    emit cp315-abi3, advertising GIL abi3 support below the requested 3.16."""
    get_config_var = sysconfig.get_config_var
    monkeypatch.setattr(
        sysconfig,
        "get_config_var",
        lambda x: "t" if x == "Py_GIL_DISABLED" else get_config_var(x),
    )
    monkeypatch.setattr(sys, "platform", "darwin")
    monkeypatch.setattr(sys, "implementation", SimpleNamespace(name="cpython"))
    monkeypatch.setenv("MACOSX_DEPLOYMENT_TARGET", "10.10")
    monkeypatch.setattr(platform, "mac_ver", lambda: ("10.9.2", "", ""))
    monkeypatch.setattr(sys, "version_info", VersionInfo(3, 16))

    with pytest.raises(AssertionError, match="must not be newer"):
        WheelTag.compute_best(["x86_64"], py_api="cp316.cp315t")

    # Equal or lower classic minor is fine (advertises no broader than requested).
    tags = WheelTag.compute_best(["x86_64"], py_api="cp314.cp315t")
    assert str(tags) == "cp315-abi3.abi3t-macosx_10_10_x86_64"


def test_wheel_tag_with_combined_abi3_abi3t_gil(monkeypatch):
    """On a GIL build, only abi3 can be produced, so cp315.cp315t emits abi3."""
    get_config_var = sysconfig.get_config_var
    monkeypatch.setattr(
        sysconfig,
        "get_config_var",
        lambda x: None if x == "Py_GIL_DISABLED" else get_config_var(x),
    )
    monkeypatch.setattr(sys, "platform", "darwin")
    monkeypatch.setattr(sys, "implementation", SimpleNamespace(name="cpython"))
    monkeypatch.setenv("MACOSX_DEPLOYMENT_TARGET", "10.10")
    monkeypatch.setattr(platform, "mac_ver", lambda: ("10.9.2", "", ""))
    monkeypatch.setattr(sys, "version_info", VersionInfo(3, 15))

    tags = WheelTag.compute_best(["x86_64"], py_api="cp315.cp315t")
    assert str(tags) == "cp315-abi3-macosx_10_10_x86_64"


def test_wheel_tag_with_classic_abi3_ignored_on_free_threaded(monkeypatch):
    """Test classic abi3 requests fall back to default tags on free-threaded Python."""
    get_config_var = sysconfig.get_config_var
    monkeypatch.setattr(
        sysconfig,
        "get_config_var",
        lambda x: "t" if x == "Py_GIL_DISABLED" else get_config_var(x),
    )
    monkeypatch.setattr(sys, "platform", "darwin")
    monkeypatch.setenv("MACOSX_DEPLOYMENT_TARGET", "10.10")
    monkeypatch.setattr(platform, "mac_ver", lambda: ("10.9.2", "", ""))

    default_tags = WheelTag.compute_best(["x86_64"])
    tags = WheelTag.compute_best(["x86_64"], py_api="cp38")
    assert tags == default_tags


def test_wheel_tag_with_abi3t_ignored_on_classic(monkeypatch):
    """Test cp315t falls back to default tags on classic (non-free-threaded) Python."""
    get_config_var = sysconfig.get_config_var
    monkeypatch.setattr(
        sysconfig,
        "get_config_var",
        lambda x: None if x == "Py_GIL_DISABLED" else get_config_var(x),
    )
    monkeypatch.setattr(sys, "platform", "darwin")
    monkeypatch.setenv("MACOSX_DEPLOYMENT_TARGET", "10.10")
    monkeypatch.setattr(platform, "mac_ver", lambda: ("10.9.2", "", ""))

    default_tags = WheelTag.compute_best(["x86_64"])
    tags = WheelTag.compute_best(["x86_64"], py_api="cp315t")
    assert tags == default_tags


def test_wheel_tag_host_platform_override(monkeypatch):
    """Test that _PYTHON_HOST_PLATFORM environment variable overrides platform detection."""
    get_config_var = sysconfig.get_config_var
    monkeypatch.setattr(
        sysconfig,
        "get_config_var",
        lambda x: None if x == "Py_GIL_DISABLED" else get_config_var(x),
    )
    monkeypatch.setattr(sys, "platform", "linux")

    monkeypatch.setenv("_PYTHON_HOST_PLATFORM", "macosx-11.0-arm64")
    tags = WheelTag.compute_best(["x86_64"], py_api="py3")
    assert str(tags) == "py3-none-macosx_11_0_arm64"

    monkeypatch.setenv("_PYTHON_HOST_PLATFORM", "emscripten-4.0.9-wasm32")
    tags = WheelTag.compute_best(["x86_64"], py_api="py3")
    assert str(tags) == "py3-none-emscripten_4_0_9_wasm32"


def test_get_soabi_abi3t(monkeypatch):
    get_config_var = sysconfig.get_config_var
    monkeypatch.setattr(
        sysconfig,
        "get_config_var",
        lambda x: "t" if x == "Py_GIL_DISABLED" else get_config_var(x),
    )

    from scikit_build_core.builder.sysconfig import get_soabi

    assert get_soabi({}, abi3t=True) == (
        "" if sysconfig.get_platform().startswith("win") else "abi3t"
    )
    assert get_soabi({}, abi3=True) == (
        "" if sysconfig.get_platform().startswith("win") else "abi3"
    )


@pytest.mark.parametrize(
    "args",
    [
        pytest.param(["-GAnything"], id="joined"),
        pytest.param(["-G", "Anything"], id="two-token"),
    ],
)
def test_generator_args(
    args: list[str], tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    monkeypatch.chdir(tmp_path)
    builder = Builder(
        settings=ScikitBuildSettings(cmake=CMakeSettings(args=args)),
        config=CMaker(
            CMake(Version("4.0"), Path("no-cmake")), Path(), Path(), "Release"
        ),
    )
    assert builder.get_generator() == "Anything"


def test_generator_define(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.chdir(tmp_path)
    builder = Builder(
        settings=ScikitBuildSettings(
            cmake=CMakeSettings(
                define={"CMAKE_GENERATOR": CMakeSettingsDefine("Anything")}
            )
        ),
        config=CMaker(
            CMake(Version("4.0"), Path("no-cmake")), Path(), Path(), "Release"
        ),
    )
    assert builder.get_generator() == "Anything"


def test_generator_env(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("CMAKE_GENERATOR", "Anything")
    builder = Builder(
        settings=ScikitBuildSettings(),
        config=CMaker(
            CMake(Version("4.0"), Path("no-cmake")), Path(), Path(), "Release"
        ),
    )
    assert builder.get_generator() == "Anything"


@pytest.mark.parametrize("generator", ["Ninja", "Ninja Multi-Config"])
def test_set_environment_for_gen_ninja_variants(
    monkeypatch: pytest.MonkeyPatch, generator: str
):
    # Both "Ninja" and "Ninja Multi-Config" must trigger ninja handling: a
    # CMAKE_MAKE_PROGRAM hint and the actual generator set in CMAKE_GENERATOR.
    from scikit_build_core.builder import generator as gen_mod
    from scikit_build_core.program_search import Program
    from scikit_build_core.settings.skbuild_model import NinjaSettings

    fake_ninja = Program(Path("/usr/bin/ninja"), Version("1.11.0"))
    monkeypatch.setattr(gen_mod, "get_ninja_programs", lambda: [fake_ninja])

    env: dict[str, str] = {}
    result = gen_mod.set_environment_for_gen(
        generator,
        CMake(Version("3.30"), Path("cmake")),
        env,
        NinjaSettings(),
    )
    assert result == {"CMAKE_MAKE_PROGRAM": str(fake_ninja.path)}
    assert env["CMAKE_GENERATOR"] == generator


def test_set_environment_for_gen_strips_cc_cxx_flags(
    monkeypatch: pytest.MonkeyPatch,
):
    # sysconfig may report CC/CXX with trailing flags (e.g. "c++ -pthread").
    # Only the executable should be exported, so flags don't leak into tools
    # like autotools sub-builds. See #1330.
    from scikit_build_core.builder import generator as gen_mod
    from scikit_build_core.program_search import Program
    from scikit_build_core.settings.skbuild_model import NinjaSettings

    fake_ninja = Program(Path("/usr/bin/ninja"), Version("1.11.0"))
    monkeypatch.setattr(gen_mod, "get_ninja_programs", lambda: [fake_ninja])
    config_vars = {"CC": "gcc -pthread", "CXX": "c++ -pthread"}
    monkeypatch.setattr(sysconfig, "get_config_var", config_vars.get)

    env: dict[str, str] = {}
    gen_mod.set_environment_for_gen(
        "Ninja",
        CMake(Version("3.30"), Path("cmake")),
        env,
        NinjaSettings(),
    )
    assert env["CC"] == "gcc"
    assert env["CXX"] == "c++"


def test_set_environment_for_gen_sysconfig_compiler(
    monkeypatch: pytest.MonkeyPatch,
):
    # By default CC/CXX from sysconfig are injected; a key managed via the env
    # table suppresses that default, letting CMake detect the compiler. See #1367.
    from scikit_build_core.builder import generator as gen_mod
    from scikit_build_core.program_search import Program
    from scikit_build_core.settings.skbuild_model import NinjaSettings

    fake_ninja = Program(Path("/usr/bin/ninja"), Version("1.11.0"))
    monkeypatch.setattr(gen_mod, "get_ninja_programs", lambda: [fake_ninja])
    config_vars = {"CC": "gcc -pthread", "CXX": "c++ -pthread"}
    monkeypatch.setattr(sysconfig, "get_config_var", config_vars.get)

    env_default: dict[str, str] = {}
    gen_mod.set_environment_for_gen(
        "Ninja",
        CMake(Version("3.30"), Path("cmake")),
        env_default,
        NinjaSettings(),
    )
    assert env_default["CC"] == "gcc"
    assert env_default["CXX"] == "c++"

    env_off: dict[str, str] = {}
    gen_mod.set_environment_for_gen(
        "Ninja",
        CMake(Version("3.30"), Path("cmake")),
        env_off,
        NinjaSettings(),
        env_managed_keys={"CC", "CXX"},
    )
    assert "CC" not in env_off
    assert "CXX" not in env_off


def test_set_environment_for_gen_ninja_multi_config_missing(
    monkeypatch: pytest.MonkeyPatch,
):
    # An explicit Ninja Multi-Config generator with no ninja must raise rather
    # than silently fall back to make.
    from scikit_build_core.builder import generator as gen_mod
    from scikit_build_core.errors import NinjaNotFoundError
    from scikit_build_core.settings.skbuild_model import NinjaSettings

    monkeypatch.setattr(gen_mod, "get_ninja_programs", list)

    with pytest.raises(NinjaNotFoundError):
        gen_mod.set_environment_for_gen(
            "Ninja Multi-Config",
            CMake(Version("3.30"), Path("cmake")),
            {},
            NinjaSettings(),
        )


def _settings_with_env(env: dict[str, typing.Any]) -> ScikitBuildSettings:
    from scikit_build_core.settings.skbuild_model import EnvValue

    return ScikitBuildSettings(env={k: EnvValue(v) for k, v in env.items()})


def test_set_environment_from_settings_setdefault():
    from scikit_build_core.builder.builder import set_environment_from_settings

    settings = _settings_with_env(
        {
            "LITERAL": "hello",
            "CMAKE_BUILD_PARALLEL_LEVEL": {"env": "MAX_JOBS"},
            "WITH_DEFAULT": {"env": "NOT_SET", "default": "fallback"},
        }
    )
    # MAX_JOBS provides the value; an already-set target var is preserved.
    env = {"MAX_JOBS": "7", "CMAKE_BUILD_PARALLEL_LEVEL": "keep"}
    set_environment_from_settings(env, settings)

    assert env["LITERAL"] == "hello"
    assert env["CMAKE_BUILD_PARALLEL_LEVEL"] == "keep"
    assert env["WITH_DEFAULT"] == "fallback"


def test_set_environment_from_settings_max_jobs_alias():
    """Regression for the PyTorch wrapper: MAX_JOBS -> CMAKE_BUILD_PARALLEL_LEVEL."""
    from scikit_build_core.builder.builder import set_environment_from_settings

    settings = _settings_with_env({"CMAKE_BUILD_PARALLEL_LEVEL": {"env": "MAX_JOBS"}})

    env = {"MAX_JOBS": "3"}
    set_environment_from_settings(env, settings)
    assert env["CMAKE_BUILD_PARALLEL_LEVEL"] == "3"

    # No MAX_JOBS and no default -> the variable is left unset.
    env_empty: dict[str, str] = {}
    set_environment_from_settings(env_empty, settings)
    assert "CMAKE_BUILD_PARALLEL_LEVEL" not in env_empty


def test_set_environment_from_settings_force():
    from scikit_build_core.builder.builder import set_environment_from_settings

    settings = _settings_with_env(
        {
            "SOFT": "soft-value",
            "HARD": {"default": "hard-value", "force": True},
        }
    )
    env = {"SOFT": "existing", "HARD": "existing"}
    set_environment_from_settings(env, settings)

    assert env["SOFT"] == "existing"
    assert env["HARD"] == "hard-value"


def test_builder_applies_env_table(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """Builder construction applies the env table to the shared CMaker env."""
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("MAX_JOBS", "5")
    monkeypatch.delenv("CMAKE_BUILD_PARALLEL_LEVEL", raising=False)

    builder = Builder(
        settings=_settings_with_env(
            {"CMAKE_BUILD_PARALLEL_LEVEL": {"env": "MAX_JOBS"}}
        ),
        config=CMaker(
            CMake(Version("4.0"), Path("no-cmake")), Path(), Path(), "Release"
        ),
    )
    assert builder.config.env["CMAKE_BUILD_PARALLEL_LEVEL"] == "5"


def test_sanitize_path_plain(tmp_path: Path):
    """A normal Path passes through as a single-element list."""
    assert _sanitize_path(tmp_path) == [tmp_path]


def test_sanitize_path_multiplexed():
    """A MultiplexedPath-like object (namespace package) yields all real paths.

    ``importlib.resources.files`` returns one of these for a namespace package,
    and it does not stringify to a usable filesystem path (issue #682).
    """

    class FakeMultiplexedPath:
        def __init__(self, *paths: str) -> None:
            self._paths = [Path(p) for p in paths]

    one = FakeMultiplexedPath("/a/ns/pkg")
    assert _sanitize_path(one) == [Path("/a/ns/pkg")]

    many = FakeMultiplexedPath("/a/ns/pkg", "/b/ns/pkg")
    assert _sanitize_path(many) == [Path("/a/ns/pkg"), Path("/b/ns/pkg")]
