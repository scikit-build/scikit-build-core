from __future__ import annotations

import shutil
import sys
from pathlib import Path
from typing import TYPE_CHECKING, ClassVar, Literal

import setuptools
import setuptools.errors
from packaging.version import Version

from .._compat import tomllib
from .._logging import LEVEL_VALUE, raw_logger
from ..builder.builder import Builder, get_archs
from ..builder.macos import normalize_macos_version
from ..cmake import CMake, CMaker
from ..settings.skbuild_read_settings import SettingsReader

if TYPE_CHECKING:
    from setuptools.dist import Distribution

    from ..settings.skbuild_model import ScikitBuildSettings

__all__ = [
    "BuildCMake",
    "cmake_args",
    "cmake_install_target",
    "cmake_source_dir",
    "finalize_distribution_options",
]


def __dir__() -> list[str]:
    return __all__


def _validate_settings(settings: ScikitBuildSettings) -> None:
    assert not settings.wheel.expand_macos_universal_tags, (
        "wheel.expand_macos_universal_tags is not supported in setuptools mode"
    )
    assert settings.logging.level == "WARNING", (
        "Logging is not adjustable in setuptools mode yet"
    )
    assert not settings.wheel.py_api, (
        "wheel.py_api is not supported in setuptools mode, use bdist_wheel options instead"
    )


def get_source_dir_from_pyproject_toml() -> str | None:
    try:
        with Path("pyproject.toml").open("rb") as f:
            source_dir: str | None = tomllib.load(f)["tool"]["scikit-build"]["cmake"][
                "source-dir"
            ]
            return source_dir
    except (FileNotFoundError, KeyError):
        return None


class BuildCMake(setuptools.Command):
    source_dir: str | None = None
    cmake_args: list[str] | str | None = None
    cmake_install_target: str | None = None

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
        ("source-dir=", "s", "directory with CMakeLists.txt"),
        ("cmake-args=", "a", "extra arguments for CMake"),
        ("cmake-install-target=", "", "CMake target to install"),
    ]

    def initialize_options(self) -> None:
        self.build_lib = None
        self.build_temp = None
        self.debug = None
        self.editable_mode = False
        self.parallel = None
        self.plat_name = None
        self.source_dir = get_source_dir_from_pyproject_toml()
        self.cmake_args = None
        self.cmake_install_target = None

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

        settings = SettingsReader.from_file("pyproject.toml").settings
        _validate_settings(settings)

        build_tmp_folder = Path(self.build_temp)
        build_temp = build_tmp_folder / "_skbuild"

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
        limited_api = bdist_wheel.py_limited_api

        # TODO: this is a hack due to moving temporary paths for isolation
        if build_temp.exists():
            shutil.rmtree(build_temp)

        cmake = CMake.default_search(version=settings.cmake.version)

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
            orig_macos = normalize_macos_version(orig_macos_str, arm=arm_only)
            config.env.setdefault("MACOSX_DEPLOYMENT_TARGET", str(orig_macos))

        builder.config.build_type = "Debug" if self.debug else settings.cmake.build_type

        # Setting the install prefix because some libs hardcode CMAKE_INSTALL_PREFIX
        # Otherwise `cmake --install --prefix` would work by itself
        install_dir = Path(self.build_lib)
        defines = {"CMAKE_INSTALL_PREFIX": install_dir}

        builder.configure(
            name=dist.get_name(),
            version=Version(dist.get_version()),
            defines=defines,
            limited_api=bool(limited_api),
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
        builder.install(install_dir=install_dir)

    # def "get_source_file"(self) -> list[str]:
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


def finalize_distribution_options(dist: Distribution) -> None:
    # Prepare new build_cmake command and make sure build calls it
    build = dist.get_command_class("build")
    assert build is not None
    if "build_cmake" not in {x for x, _ in build.sub_commands}:
        build.sub_commands.append(
            ("build_cmake", lambda cmd: _has_cmake(cmd.distribution))
        )
    if get_source_dir_from_pyproject_toml() is not None:
        _cmake_extension(dist)


def _cmake_extension(dist: Distribution) -> None:
    # Every keyword argument needs to call this
    # Run this only once
    if getattr(dist, "_has_cmake_extensions", False):
        return

    # pylint: disable-next=protected-access
    dist._has_cmake_extensions = True  # type: ignore[attr-defined]

    # Setuptools needs to know that it has extensions modules
    orig_has_ext_modules = dist.has_ext_modules
    dist.has_ext_modules = lambda: orig_has_ext_modules() or _has_cmake(dist)  # type: ignore[method-assign]

    # Hack for stdlib distutils
    if not setuptools.distutils.__package__.startswith("setuptools"):  # type: ignore[attr-defined]

        class EvilList(list):  # type: ignore[type-arg]
            def __len__(self) -> int:
                return super().__len__() or int(_has_cmake(dist))

        dist.ext_modules = getattr(dist, "ext_modules", []) or EvilList()

    # Setup logging
    settings = SettingsReader.from_file("pyproject.toml").settings
    level_value = LEVEL_VALUE[settings.logging.level]
    raw_logger.setLevel(level_value)


def cmake_args(
    dist: Distribution, attr: Literal["cmake_args"], value: list[str]
) -> None:
    assert attr == "cmake_args"
    _cmake_extension(dist)
    if not isinstance(value, list):
        msg = "cmake_args must be a list"
        raise setuptools.errors.SetupError(msg)


def cmake_source_dir(
    dist: Distribution, attr: Literal["cmake_source_dir"], value: str
) -> None:
    assert attr == "cmake_source_dir"
    if get_source_dir_from_pyproject_toml() is not None:
        msg = "cmake_source_dir is already defined in pyproject.toml"
        raise setuptools.errors.SetupError(msg)
    _cmake_extension(dist)
    if not Path(value).is_dir():
        msg = "cmake_source_dir must be an existing directory"
        raise setuptools.errors.SetupError(msg)


def cmake_install_target(
    dist: Distribution, attr: Literal["cmake_install_target"], value: str
) -> None:
    assert attr == "cmake_install_target"
    assert value is not None
    _cmake_extension(dist)
    msg = "cmake_install_target is not supported - please use components and build targets instead"
    raise setuptools.errors.SetupError(msg)
