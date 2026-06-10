from __future__ import annotations

import os
import shutil
import sysconfig
from pathlib import Path
from typing import List, Union

import pytest
from packaging.specifiers import SpecifierSet

from scikit_build_core.cmake import CMake, CMaker
from scikit_build_core.file_api._cattrs_converter import (
    load_reply_dir as load_reply_dir_cattrs,
)
from scikit_build_core.file_api.model.codemodel import Link
from scikit_build_core.file_api.model.common import Paths
from scikit_build_core.file_api.query import stateless_query
from scikit_build_core.file_api.reply import Converter, load_reply_dir

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


@pytest.mark.configure
def test_cattrs_comparison(tmp_path):
    build_dir = tmp_path / "build"

    cmake = CMake.default_search(version=SpecifierSet(">=3.15"))
    config = CMaker(
        cmake,
        source_dir=DIR / "packages/simple_pure",
        build_dir=build_dir,
        build_type="Release",
    )

    reply_dir = stateless_query(config.build_dir)

    config.configure()

    cattrs_index = load_reply_dir_cattrs(reply_dir)
    index = load_reply_dir(reply_dir)
    assert index == cattrs_index


def test_convert_union_matches_shape():
    # ``InstallRule.paths`` is a ``List[Union[str, Paths]]``. A bare string must
    # stay a string, while a mapping must be converted to the dataclass member
    # (``str(<dict>)`` would otherwise succeed and shadow ``Paths``).
    converter = Converter(Path())
    result = converter._convert_any(
        ["a/string", {"source": "src/dir", "build": "build/dir"}],
        List[Union[str, Paths]],
    )
    assert result == [
        "a/string",
        Paths(source=Path("src/dir"), build=Path("build/dir")),
    ]


def test_link_without_command_fragments():
    # ``commandFragments`` is optional per the CMake File API spec; a link
    # object omitting it must still structure rather than failing conversion.
    converter = Converter(Path())
    result = converter._convert_any({"language": "CXX"}, Link)
    assert result == Link(language="CXX")
    assert result.commandFragments == []


# TODO: Why is this an IndexError?
def test_no_index(tmp_path):
    with pytest.raises(IndexError):
        load_reply_dir(tmp_path)

    with pytest.raises(IndexError):
        load_reply_dir_cattrs(tmp_path)


@pytest.mark.configure
def test_simple_pure(tmp_path):
    build_dir = tmp_path / "build"

    cmake = CMake.default_search(version=SpecifierSet(">=3.15"))
    config = CMaker(
        cmake,
        source_dir=DIR / "packages/simple_pure",
        build_dir=build_dir,
        build_type="Release",
    )

    reply_dir = stateless_query(config.build_dir)
    config.configure()
    index = load_reply_dir(reply_dir)

    codemodel = index.reply.codemodel_v2
    assert codemodel is not None

    cache = index.reply.cache_v2
    assert cache is not None

    cmakefiles = index.reply.cmakefiles_v1
    assert cmakefiles is not None

    toolchains = index.reply.toolchains_v1
    assert toolchains is not None


def test_included_dir():
    reply_dir = DIR / "api/simple_pure/.cmake/api/v1/reply"

    index = load_reply_dir(reply_dir)

    assert index.cmake.version.string == "3.24.1"
    assert index.cmake.generator.name == "Ninja"
    assert len(index.objects) == 4

    codemodel = index.reply.codemodel_v2
    assert codemodel is not None
    assert codemodel.kind == "codemodel"
    assert codemodel.version.major == 2
    assert codemodel.version.minor == 4
    assert not codemodel.configurations[0].name

    cache = index.reply.cache_v2
    assert cache is not None

    cmakefiles = index.reply.cmakefiles_v1
    assert cmakefiles is not None

    toolchains = index.reply.toolchains_v1
    assert toolchains is not None
    # The populated toolchains-v1-*.json must actually be followed and parsed,
    # not silently structured into an empty stub.
    assert toolchains.kind == "toolchains"
    assert toolchains.version.major == 1
    assert len(toolchains.toolchains) == 1
    (toolchain,) = toolchains.toolchains
    assert toolchain.language == "CXX"
    assert toolchain.compiler.id == "AppleClang"
    assert toolchain.sourceFileExtensions
    assert toolchain.compiler.implicit.includeDirectories

    # The cattrs-based converter must load the same toolchain content.
    cattrs_index = load_reply_dir_cattrs(reply_dir)
    assert cattrs_index.reply.toolchains_v1 is not None
    assert cattrs_index.reply.toolchains_v1.toolchains == toolchains.toolchains
