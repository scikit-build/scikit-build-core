from __future__ import annotations

import os
import shutil
import sysconfig
from pathlib import Path

import pytest
from packaging.specifiers import SpecifierSet

from scikit_build_core.cmake import CMake, CMaker
from scikit_build_core.file_api._cattrs_converter import (
    load_reply_dir as load_reply_dir_cattrs,
)
from scikit_build_core.file_api._cattrs_converter import (
    make_converter,
)
from scikit_build_core.file_api.model.codemodel import (
    CompileCommandFragment,
    CompileDependency,
    CompileGroup,
    Debugger,
    Define,
    Dependency,
    FileSet,
    Folder,
    FromDependency,
    Include,
    LanguageStandard,
    Launcher,
    Link,
    LinkLibrary,
    PrecompileHeader,
    Source,
    SourceGroup,
    Sysroot,
    Target,
)
from scikit_build_core.file_api.model.common import APIVersion
from scikit_build_core.file_api.model.directory import InstallPath, InstallRule
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


def test_convert_install_rule():
    # ``InstallRule.paths`` entries are strings or ``{"from", "to"}`` objects
    # (e.g. ``install(FILES ... RENAME)``). A bare string must become a Path,
    # while a mapping must be converted to the dataclass member
    # (``Path(<dict>)`` would otherwise be tried and shadow ``InstallPath``).
    data = {
        "component": "Unspecified",
        "type": "file",
        "destination": "include",
        "paths": ["a/string", {"from": "src/file.h", "to": "renamed.h"}],
        "targetInstallNamelink": "skip",
    }
    expected = InstallRule(
        component="Unspecified",
        type="file",
        destination=Path("include"),
        paths=[
            Path("a/string"),
            InstallPath(from_=Path("src/file.h"), to=Path("renamed.h")),
        ],
        targetInstallNamelink="skip",
    )

    converter = Converter(Path())
    assert converter._convert_any(data, InstallRule) == expected

    cattrs_converter = make_converter(Path())
    assert cattrs_converter.structure(data, InstallRule) == expected


def test_convert_compile_group():
    converter = Converter(Path())
    data = {
        "sourceIndexes": [0],
        "language": "CXX",
        "languageStandard": {"backtraces": [3], "standard": "17"},
        "compileCommandFragments": [{"fragment": "-fvisibility=hidden"}],
        "includes": [{"path": "/usr/include/python3.13", "isSystem": True}],
        "frameworks": [{"path": "/Library/Frameworks"}],
        "precompileHeaders": [{"header": "pch.hpp", "backtrace": 1}],
        "defines": [{"define": "VERSION=1", "backtrace": 2}],
        "sysroot": {"path": "/sdk"},
    }
    assert converter._convert_any(data, CompileGroup) == CompileGroup(
        sourceIndexes=[0],
        language="CXX",
        languageStandard=LanguageStandard(standard="17", backtraces=[3]),
        compileCommandFragments=[
            CompileCommandFragment(fragment="-fvisibility=hidden")
        ],
        includes=[Include(path=Path("/usr/include/python3.13"), isSystem=True)],
        frameworks=[Include(path=Path("/Library/Frameworks"))],
        precompileHeaders=[PrecompileHeader(header=Path("pch.hpp"), backtrace=1)],
        defines=[Define(define="VERSION=1", backtrace=2)],
        sysroot=Sysroot(path=Path("/sdk")),
    )


def test_convert_target_relationships():
    converter = Converter(Path())
    data = {
        "name": "mylib",
        "id": "mylib::@1",
        "type": "SHARED_LIBRARY",
        "paths": {"source": ".", "build": "."},
        "folder": {"name": "libs"},
        "launchers": [{"command": "emu", "arguments": ["-t"], "type": "emulator"}],
        "debugger": {"workingDirectory": "/wd"},
        "imported": True,
        "linkLibraries": [
            {"id": "dep::@1", "backtrace": 1},
            {"fragment": "-lm"},
            {"id": "extra::@2", "fromDependency": {"id": "dep::@1"}},
        ],
        "interfaceLinkLibraries": [{"id": "dep::@1"}],
        "compileDependencies": [{"id": "dep::@1", "fromDependency": {"id": "x::@9"}}],
        "orderDependencies": [{"id": "other::@3", "backtrace": 2}],
        "objectDependencies": [{"id": "objs::@4"}],
        "fileSets": [
            {
                "name": "HEADERS",
                "type": "HEADERS",
                "visibility": "PUBLIC",
                "baseDirectories": ["include"],
            }
        ],
        "sources": [{"path": "a.cpp", "fileSetIndexes": [0], "backtraces": [1]}],
        "codemodelVersion": {"major": 2, "minor": 9},
    }
    target = converter._convert_any(data, Target)
    assert target.folder == Folder(name="libs")
    assert target.launchers == [
        Launcher(command=Path("emu"), arguments=["-t"], type="emulator")
    ]
    assert target.debugger == Debugger(workingDirectory=Path("/wd"))
    assert target.imported is True
    assert target.linkLibraries == [
        LinkLibrary(id="dep::@1", backtrace=1),
        LinkLibrary(fragment="-lm"),
        LinkLibrary(id="extra::@2", fromDependency=FromDependency(id="dep::@1")),
    ]
    assert target.interfaceLinkLibraries == [LinkLibrary(id="dep::@1")]
    assert target.compileDependencies == [
        CompileDependency(id="dep::@1", fromDependency=FromDependency(id="x::@9"))
    ]
    assert target.orderDependencies == [Dependency(id="other::@3", backtrace=2)]
    assert target.objectDependencies == [Dependency(id="objs::@4")]
    assert target.fileSets == [
        FileSet(
            name="HEADERS",
            type="HEADERS",
            visibility="PUBLIC",
            baseDirectories=[Path("include")],
        )
    ]
    assert target.sources == [
        Source(path=Path("a.cpp"), fileSetIndexes=[0], backtraces=[1])
    ]
    assert target.codemodelVersion == APIVersion(2, 9)


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

    # Reference-only members must be kept when following jsonFile
    (target,) = codemodel.configurations[0].targets
    assert target.directoryIndex == 0
    assert target.projectIndex == 0
    assert target.type == "EXECUTABLE"
    assert target.backtrace == 1
    assert target.sourceGroups == [SourceGroup(name="Source Files", sourceIndexes=[0])]
    (compile_group,) = target.compileGroups
    assert compile_group.language == "CXX"
    assert compile_group.languageStandard == LanguageStandard(
        standard="17", backtraces=[3]
    )
    assert target.backtraceGraph is not None
    assert target.backtraceGraph.commands == [
        "add_executable",
        "install",
        "target_compile_features",
    ]

    # The directory object must be followed and merged with its reference
    (directory,) = codemodel.configurations[0].directories
    assert directory.jsonFile is not None
    assert directory.hasInstallRule
    (installer,) = directory.installers
    assert installer.component == "Unspecified"
    assert installer.type == "target"
    assert installer.destination == Path("bin")
    assert installer.targetIndex == 0
    assert installer.paths == [Path("simple_pure")]
    assert installer.backtrace == 1
    assert directory.backtraceGraph is not None
    assert directory.backtraceGraph.commands == ["install"]

    cache = index.reply.cache_v2
    assert cache is not None

    cmakefiles = index.reply.cmakefiles_v1
    assert cmakefiles is not None
    assert cmakefiles.version == APIVersion(1, 0)

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

    # The cattrs-based converter must load the same content.
    cattrs_index = load_reply_dir_cattrs(reply_dir)
    assert cattrs_index == index
