from __future__ import annotations

import os
import shutil
import sysconfig
from pathlib import Path
from typing import TYPE_CHECKING

import pytest
from packaging.specifiers import SpecifierSet
from packaging.version import Version

from scikit_build_core.cmake import CMake, CMaker
from scikit_build_core.errors import CMakeNotFoundError

if TYPE_CHECKING:
    from collections.abc import Generator

    from _pytest.mark.structures import ParameterSet

DIR = Path(__file__).parent.resolve()


def get_cmake_configure_test_parameters() -> tuple[tuple[str, str], list[ParameterSet]]:
    win_marks = []
    linux_or_darwin_marks = []
    if sysconfig.get_platform().startswith("win"):
        linux_or_darwin_marks = [pytest.mark.skip(reason="run only on Linux/Darwin")]
    else:
        win_marks = [pytest.mark.skip(reason="run only on Windows")]
    return ("generator", "single_config"), [
        # windows
        pytest.param(None, False, marks=win_marks, id="only_win_round"),
        pytest.param("Ninja", True, marks=win_marks, id="win_ninja_round"),
        pytest.param("Makefiles", True, marks=win_marks, id="win_makefiles_round"),
        pytest.param("Others", False, marks=win_marks, id="win_others_round"),
        # linux or darwin
        pytest.param(None, True, marks=linux_or_darwin_marks, id="only_linux_round"),
        pytest.param(
            "Ninja", True, marks=linux_or_darwin_marks, id="linux_ninja_round"
        ),
    ]


def configure_cmake_configure_test(
    generator: str | None,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    if generator is None:
        monkeypatch.delenv("CMAKE_GENERATOR", raising=False)
    else:
        monkeypatch.setenv("CMAKE_GENERATOR", generator)


def configure_args(
    config: CMaker, *, init: bool = False, single_config: bool = False
) -> Generator[str, None, None]:
    yield f"-S{config.source_dir}"
    yield f"-B{config.build_dir}"

    if single_config:
        yield f"-DCMAKE_BUILD_TYPE:STRING={config.build_type}"

    if init:
        cmake_init = config.build_dir / "CMakeInit.txt"
        yield f"-C{cmake_init}"


@pytest.mark.configure()
@pytest.mark.parametrize(*get_cmake_configure_test_parameters())
def test_init_cache(
    generator: str,
    single_config: bool,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    fp,
):
    fp.register(
        [fp.program("cmake"), "-E", "capabilities"],
        stdout='{"version":{"string":"3.14.0"}}',
    )
    fp.register(
        [fp.program("cmake3"), "-E", "capabilities"],
        stdout='{"version":{"string":"3.14.0"}}',
    )

    configure_cmake_configure_test(generator, monkeypatch)

    config = CMaker(
        CMake.default_search(),
        source_dir=DIR / "packages/simple_pure",
        build_dir=tmp_path / "build",
        build_type="Release",
    )
    config.init_cache(
        {"SKBUILD": True, "SKBUILD_VERSION": "1.0.0", "SKBUILD_PATH": config.source_dir}
    )

    cmd = list(configure_args(config, init=True, single_config=single_config))
    print("Registering: cmake", *cmd)
    fp.register([fp.program("cmake"), *cmd])
    fp.register([fp.program("cmake3"), *cmd])
    config.configure()

    cmake_init = config.build_dir / "CMakeInit.txt"
    source_dir_str = str(config.source_dir).replace("\\", "/")
    assert (
        cmake_init.read_text()
        == f"""\
set(SKBUILD ON CACHE BOOL "" FORCE)
set(SKBUILD_VERSION [===[1.0.0]===] CACHE STRING "" FORCE)
set(SKBUILD_PATH [===[{source_dir_str}]===] CACHE PATH "" FORCE)
"""
    )


@pytest.mark.configure()
def test_too_old(fp, monkeypatch):
    monkeypatch.setattr(shutil, "which", lambda _: None)
    fp.register(
        [fp.program("cmake"), "-E", "capabilities"],
        stdout='{"version":{"string":"3.14.0"}}',
    )
    fp.register(
        [fp.program("cmake3"), "-E", "capabilities"],
        stdout='{"version":{"string":"3.14.0"}}',
    )

    with pytest.raises(CMakeNotFoundError) as excinfo:
        CMake.default_search(version=SpecifierSet(">=3.15"))
    assert "Could not find CMake with version >=3.15" in excinfo.value.args[0]


@pytest.mark.configure()
@pytest.mark.parametrize(*get_cmake_configure_test_parameters())
def test_cmake_args(
    generator: str,
    single_config: bool,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    fp,
):
    fp.register(
        [fp.program("cmake"), "-E", "capabilities"],
        stdout='{"version":{"string":"3.15.0"}}',
    )
    fp.register(
        [fp.program("cmake3"), "-E", "capabilities"],
        stdout='{"version":{"string":"3.15.0"}}',
    )

    configure_cmake_configure_test(generator, monkeypatch)

    config = CMaker(
        CMake.default_search(),
        source_dir=DIR / "packages" / "simple_pure",
        build_dir=tmp_path / "build",
        build_type="Release",
    )

    cmd = list(configure_args(config, single_config=single_config))
    cmd.append("-DSOMETHING=one")
    print("Registering: cmake", *cmd)
    fp.register([fp.program("cmake"), *cmd])
    fp.register([fp.program("cmake3"), *cmd])

    config.configure(cmake_args=["-DSOMETHING=one"])
    # config.configure might mutate config.single_config
    assert config.single_config == single_config
    assert len(fp.calls) == 2


@pytest.mark.configure()
@pytest.mark.parametrize(*get_cmake_configure_test_parameters())
def test_cmake_paths(
    generator: str,
    single_config: bool,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    fp,
):
    fp.register(
        [fp.program("cmake"), "-E", "capabilities"],
        stdout='{"version":{"string":"3.15.0"}}',
    )
    fp.register(
        [fp.program("cmake3"), "-E", "capabilities"],
        stdout='{"version":{"string":"3.15.0"}}',
    )

    configure_cmake_configure_test(generator, monkeypatch)

    config = CMaker(
        CMake.default_search(),
        source_dir=DIR / "packages/simple_pure",
        build_dir=tmp_path / "build",
        build_type="Release",
        prefix_dirs=[tmp_path / "prefix"],
        module_dirs=[tmp_path / "module"],
    )

    cmd = list(configure_args(config, single_config=single_config))
    print("Registering: cmake", *cmd)
    fp.register([fp.program("cmake"), *cmd])
    fp.register([fp.program("cmake3"), *cmd])

    config.configure()

    assert len(fp.calls) == 2


def test_get_cmake_via_envvar(monkeypatch: pytest.MonkeyPatch, fp):
    monkeypatch.setattr("shutil.which", lambda x: x)
    cmake_path = Path("some-prog")
    fp.register(
        [cmake_path, "-E", "capabilities"], stdout='{"version":{"string":"3.20.0"}}'
    )
    monkeypatch.setenv("CMAKE_EXECUTABLE", str(cmake_path))
    result = CMake.default_search(env=os.environ)
    assert result.cmake_path == cmake_path
    assert result.version == Version("3.20.0")
