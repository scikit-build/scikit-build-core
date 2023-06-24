from __future__ import annotations

import os
import shutil
import sys
from pathlib import Path
from typing import ClassVar

import setuptools
import setuptools.errors
from packaging.version import Version
from setuptools.dist import Distribution

from .._compat.typing import Literal
from ..builder.builder import Builder, get_archs
from ..builder.macos import normalize_macos_version
from ..cmake import CMake, CMaker
from ..settings.skbuild_read_settings import SettingsReader

__all__: list[str] = ["BuildCMake", "finalize_distribution_options", "cmake_source_dir"]


def __dir__() -> list[str]:
    return __all__


def _validate_settings() -> None:
    settings = SettingsReader.from_file("pyproject.toml", {}).settings

    assert (
        not settings.wheel.expand_macos_universal_tags
    ), "wheel.expand_macos_universal_tags is not supported in setuptools mode"
    assert (
        settings.logging.level == "WARNING"
    ), "Logging is not adjustable in setuptools mode yet"
    assert (
        not settings.wheel.py_api
    ), "wheel.py_api is not supported in setuptools mode, use bdist_wheel options instead"


class BuildCMake(setuptools.Command):
    source_dir: str | None = None
    cmake_args: list[str] | str | None = None

    build_lib: str | None
    build_temp: str | None
    debug: bool | None
    editable_mode: bool
    parallel: int | None
    plat_name: str | None

    user_options: ClassVar[list[tuple[str, str, str]]] = [
        ("build-lib=", "b", "directory for compiled extension modules"),
        ("build-temp=", "t", "directory for temporary files (build by-products)"),
        ("plat-name=", "p", "platform name to cross-compile for, if supported "),
        ("debug", "g", "compile/link with debugging information"),
        ("parallel=", "j", "number of parallel build jobs"),
        ("source-dir=", "j", "directory with CMakeLists.txt"),
        ("cmake-args=", "a", "extra arguments for CMake"),
    ]

    def initialize_options(self) -> None:
        self.build_lib = None
        self.build_temp = None
        self.debug = None
        self.editable_mode = False
        self.parallel = None
        self.plat_name = None
        self.source_dir = None
        self.cmake_args = None

    def finalize_options(self) -> None:
        self.set_undefined_options(
            "build_ext",
            ("build_lib", "build_lib"),
            ("build_temp", "build_temp"),
            ("debug", "debug"),
            ("parallel", "parallel"),
            ("plat_name", "plat_name"),
        )

        if isinstance(self.cmake_args, str):
            self.cmake_args = [
                b.strip() for a in self.cmake_args.split() for b in a.split(";")
            ]

    def run(self) -> None:
        assert self.build_lib is not None
        assert self.build_temp is not None
        assert self.plat_name is not None

        _validate_settings()

        build_tmp_folder = Path(self.build_temp)
        build_temp = build_tmp_folder / "_skbuild"  # TODO: include python platform

        dist = self.distribution
        dist_source_dir = getattr(self.distribution, "cmake_source_dir", None)
        source_dir = self.source_dir if dist_source_dir is None else dist_source_dir
        assert source_dir is not None, "This should not be reachable"

        configure_args = self.cmake_args or []
        assert isinstance(configure_args, list)
        dist_cmake_args = getattr(self.distribution, "cmake_args", None)
        configure_args.extend(dist_cmake_args or [])

        bdist_wheel = dist.get_command_obj("bdist_wheel")
        assert bdist_wheel is not None
        limited_api = bdist_wheel.py_limited_api  # type: ignore[attr-defined]

        # TODO: this is a hack due to moving temporary paths for isolation
        if build_temp.exists():
            shutil.rmtree(build_temp)

        settings = SettingsReader.from_file("pyproject.toml", {}).settings

        cmake = CMake.default_search(
            minimum_version=Version(settings.cmake.minimum_version)
        )

        config = CMaker(
            cmake,
            source_dir=Path(source_dir),
            build_dir=build_temp,
            build_type=settings.cmake.build_type,
        )

        builder = Builder(
            settings=settings,
            config=config,
        )

        # Setuptools requires this be specified if there's a mismatch.
        if sys.platform.startswith("darwin"):
            arm_only = get_archs(builder.config.env) == ["arm64"]
            orig_macos_str = self.plat_name.rsplit("-", 1)[0].split("-", 1)[1]
            orig_macos = normalize_macos_version(orig_macos_str, arm_only)
            config.env.setdefault("MACOSX_DEPLOYMENT_TARGET", str(orig_macos))

        debug = int(os.environ.get("DEBUG", 0)) if self.debug is None else self.debug
        builder.config.build_type = "Debug" if debug else "Release"

        builder.configure(
            name=dist.get_name(),
            version=Version(dist.get_version()),
            defines={},
            limited_abi=limited_api,
            configure_args=configure_args,
        )

        # Set CMAKE_BUILD_PARALLEL_LEVEL to control the parallel build level
        # across all generators.
        build_args = []

        # self.parallel is a way to set parallel jobs by hand using -j in the
        # build_ext call, not supported by pip or PyPA-build.
        if "CMAKE_BUILD_PARALLEL_LEVEL" not in builder.config.env and self.parallel:
            build_args.append(f"-j{self.parallel}")

        builder.build(build_args=build_args)
        builder.install(Path(self.build_lib))

    # def "get_source_file+ys"(self) -> list[str]:
    #    return ["CMakeLists.txt"]

    # def get_outputs(self) -> list[str]:
    #    return []

    # def get_output_mapping(self) -> dict[str, str]:
    #    return {}


def _has_cmake(dist: Distribution) -> bool:
    build_cmake = dist.get_command_obj("build_cmake")
    assert isinstance(build_cmake, BuildCMake)
    return (
        build_cmake.source_dir is not None
        or getattr(dist, "cmake_source_dir", None) is not None
    )


def _prepare_extension_detection(dist: Distribution) -> None:
    # Setuptools needs to know that it has extensions modules

    dist.has_ext_modules = lambda: type(dist).has_ext_modules(dist) or _has_cmake(dist)  # type: ignore[method-assign]

    # Hack for stdlib distutils
    if not setuptools.distutils.__package__.startswith("setuptools"):  # type: ignore[attr-defined]

        class EvilList(list):  # type: ignore[type-arg]
            def __len__(self) -> int:
                return super().__len__() or int(_has_cmake(dist))

        dist.ext_modules = getattr(dist, "ext_modules", []) or EvilList()


def _prepare_build_cmake_command(dist: Distribution) -> None:
    # Prepare new build_cmake command and make sure build calls it
    build = dist.get_command_obj("build")
    assert build is not None
    if "build_cmake" not in {x for x, _ in build.sub_commands}:
        build.sub_commands.append(
            ("build_cmake", lambda cmd: _has_cmake(cmd.distribution))  # type: ignore[arg-type]
        )


def cmake_args(
    _dist: Distribution, attr: Literal["cmake_args"], value: list[str]
) -> None:
    assert attr == "cmake_args"
    if not isinstance(value, list):
        msg = "cmake_args must be a list"
        raise setuptools.errors.SetupError(msg)


def cmake_source_dir(
    _dist: Distribution, attr: Literal["cmake_source_dir"], value: str
) -> None:
    assert attr == "cmake_source_dir"
    if not Path(value).is_dir():
        msg = "cmake_source_dir must be an existing directory"
        raise setuptools.errors.SetupError(msg)


def finalize_distribution_options(dist: Distribution) -> None:
    _prepare_extension_detection(dist)
    _prepare_build_cmake_command(dist)
