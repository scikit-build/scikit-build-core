from __future__ import annotations

import os
import shutil
import sys
import sysconfig
from pathlib import Path

import setuptools
from packaging.version import Version
from setuptools.dist import Distribution

from .._compat.typing import Literal
from ..builder.builder import Builder, get_archs
from ..builder.macos import normalize_macos_version
from ..cmake import CMake, CMaker
from ..settings.skbuild_read_settings import SettingsReader

__all__: list[str] = ["CMakeBuild", "cmake_extensions"]


def __dir__() -> list[str]:
    return __all__


class CMakeBuild(setuptools.Command):
    build_lib: str | None = None
    editable_mode: bool = False
    source_dir: str

    def initialize_options(self) -> None:
        pass

    def finalize_options(self) -> None:
        self.set_undefined_options("build", ("build_lib", "build_lib"))

    def run(self) -> None:
        assert self.build_lib is not None

        build_tmp_folder = Path.cwd().resolve() / "build"
        build_temp = build_tmp_folder / "_skbuild"  # TODO: include python platform

        dist = self.distribution

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
            source_dir=Path(self.source_dir),
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
            orig_macos_str = sysconfig.get_platform().rsplit("-", 1)[0].split("-", 1)[1]
            orig_macos = normalize_macos_version(orig_macos_str, arm_only)
            config.env.setdefault("MACOSX_DEPLOYMENT_TARGET", str(orig_macos))

        debug = int(os.environ.get("DEBUG", 0))
        builder.config.build_type = "Debug" if debug else "Release"

        builder.configure(
            name=dist.get_name(),
            version=Version(dist.get_version()),
            defines={},
            limited_abi=limited_api,
        )

        # Set CMAKE_BUILD_PARALLEL_LEVEL to control the parallel build level
        # across all generators.
        build_args = []

        # self.parallel is a Python 3 only way to set parallel jobs by hand
        # using -j in the build_ext call, not supported by pip or PyPA-build.
        if (
            "CMAKE_BUILD_PARALLEL_LEVEL" not in builder.config.env
            and hasattr(self, "parallel")
            and self.parallel
        ):
            build_args.append(f"-j{self.parallel}")

        builder.build(build_args=build_args)
        builder.install(Path(self.build_lib))

    # def get_source_files(self) -> list[str]:
    #    return ["CMakeLists.txt"]

    # def get_outputs(self) -> list[str]:
    #    return []

    # def get_output_mapping(self) -> dict[str, str]:
    #    return {}


def cmake_extensions(
    dist: Distribution, attr: Literal["cmake_extensions"], source_dir: str
) -> None:
    settings = SettingsReader.from_file("pyproject.toml", {}).settings

    assert attr == "cmake_extensions"
    assert source_dir

    assert (
        not settings.wheel.expand_macos_universal_tags
    ), "wheel.expand_macos_universal_tags is not supported in setuptools mode"
    assert (
        settings.logging.level == "WARNING"
    ), "Logging is not adjustable in setuptools mode yet"
    assert (
        not settings.wheel.py_api
    ), "wheel.py_api is not supported in setuptools mode, use bdist_wheel options instead"

    dist.has_ext_modules = lambda: True  # type: ignore[method-assign]
    # Hack for stdlib distutils
    if not setuptools.distutils.__package__.startswith("setuptools"):  # type: ignore[attr-defined]

        class EvilList(list):  # type: ignore[type-arg]
            def __len__(self) -> int:
                return super().__len__() or 1

        dist.ext_modules = getattr(dist, "ext_modules", []) or EvilList()

    build = dist.get_command_obj("build")
    assert build is not None
    dist.cmdclass["build_cmake"] = CMakeBuild
    dist.get_command_obj("build_cmake").source_dir = source_dir  # type: ignore[union-attr]
    if "build_cmake" not in {x for x, _ in build.sub_commands}:
        build.sub_commands.append(("build_cmake", None))


def cmake_source_dir(
    dist: Distribution, attr: Literal["cmake_source_dir"], value: str
) -> None:
    assert attr == "cmake_source_dir"
    assert Path(value).is_dir()

    cmake_extensions(dist, "cmake_extensions", value)
