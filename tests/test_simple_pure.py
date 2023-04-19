from __future__ import annotations

import os
import shutil
import subprocess
import sys
import sysconfig
from pathlib import Path

import pytest
from packaging.version import Version

from scikit_build_core.cmake import CMake, CMaker

DIR = Path(__file__).parent.absolute()


has_make = shutil.which("make") is not None or shutil.which("gmake") is not None
has_ninja = shutil.which("ninja") is not None


def prepare_env_or_skip() -> None:
    if (
        "CMAKE_GENERATOR" not in os.environ
        and not sysconfig.get_platform().startswith("win")
        and not has_make
    ):
        if has_ninja:
            os.environ["CMAKE_GENERATOR"] = "Ninja"
        else:
            pytest.skip("No build system found")


@pytest.fixture(scope="session")
def config(tmp_path_factory):
    prepare_env_or_skip()

    tmp_path = tmp_path_factory.mktemp("build")

    build_dir = tmp_path / "build"

    cmake = CMake.default_search(minimum_version=Version("3.15"))
    config = CMaker(
        cmake,
        source_dir=DIR / "packages/simple_pure",
        build_dir=build_dir,
        build_type="Release",
    )

    config.configure()

    config.build()

    return config


# TODO: figure out why gmake is reporting no rule to make simple_pure.cpp
@pytest.mark.compile()
@pytest.mark.configure()
@pytest.mark.xfail(
    sys.platform.startswith("cygwin"),
    strict=False,
    reason="No idea why this fails on Cygwin",
)
def test_bin_in_config(config):
    # TODO: this should use config.single_config, but that's not always correct currently
    pkg = config.build_dir / (
        "Release/simple_pure"
        if config.build_dir.joinpath("Release").is_dir()
        else "simple_pure"
    )
    result = subprocess.run(
        [str(pkg)],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0
    assert result.stdout == "0 one 2 three \n"


# TODO: figure out why gmake is reporting no rule to make simple_pure.cpp
@pytest.mark.compile()
@pytest.mark.configure()
@pytest.mark.xfail(
    sys.platform.startswith("cygwin"),
    strict=False,
    reason="No idea why this fails on Cygwin",
)
def test_install(config):
    install_dir = config.build_dir.parent / "install"
    config.install(install_dir)

    result = subprocess.run(
        [str(install_dir / "bin/simple_pure")],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0
    assert result.stdout == "0 one 2 three \n"


@pytest.mark.configure()
def test_variable_defined(tmp_path, capfd):
    prepare_env_or_skip()

    build_dir = tmp_path / "build"

    cmake = CMake.default_search(minimum_version=Version("3.15"))
    config = CMaker(
        cmake,
        source_dir=DIR / "packages/simple_pure",
        build_dir=build_dir,
        build_type="Release",
    )
    config.init_cache({"SKBUILD": True})
    config.configure(defines={"SKBUILD2": True})

    out = capfd.readouterr().out
    assert "SKBUILD is defined to ON" in out
    assert "SKBUILD2 is defined to ON" in out
