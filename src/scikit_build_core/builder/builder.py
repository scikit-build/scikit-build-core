from __future__ import annotations

import dataclasses
import enum
import os
import platform
import re
import shlex
import sys
import sysconfig
from pathlib import Path
from typing import Any

from .. import __version__
from .._compat.importlib import metadata, resources
from .._logging import logger
from .._reproducible import get_reproducible_epoch
from ..program_search import _macos_binary_is_x86
from ..resources import find_python
from .generator import set_environment_for_gen
from .sysconfig import (
    get_numpy_include_dir,
    get_platform,
    get_python_include_dir,
    get_python_library,
    get_soabi,
)

TYPE_CHECKING = False
if TYPE_CHECKING:
    from collections.abc import Generator, Iterable, Mapping, Sequence

    from packaging.version import Version

    from ..cmake import CMaker
    from ..settings.skbuild_model import ScikitBuildSettings

__all__ = [
    "Builder",
    "archs_to_tags",
    "get_archs",
    "get_cmake_args_from_settings",
    "set_environment_from_settings",
]

DIR = Path(__file__).parent.resolve()


class _SabiMode(enum.Enum):
    NONE = enum.auto()
    ABI3 = enum.auto()
    ABI3T = enum.auto()


def __dir__() -> list[str]:
    return __all__


# TODO: cross-compile support for other platforms
def get_archs(env: Mapping[str, str], cmake_args: Sequence[str] = ()) -> list[str]:
    """
    Takes macOS platform settings and returns a list of platforms.

    Example (macOS):
        ARCHFLAGS="-arch x86_64" -> ["x86_64"]
        ARCHFLAGS="-arch x86_64 -arch arm64" -> ["x86_64", "arm64"]

    Returns an empty list otherwise or if ARCHFLAGS is not set.
    """

    if sys.platform.startswith("darwin"):
        for cmake_arg in cmake_args:
            if "CMAKE_SYSTEM_PROCESSOR" in cmake_arg:
                return [cmake_arg.split("=")[1]]
        return re.findall(r"-arch (\S+)", env.get("ARCHFLAGS", ""))
    if sys.platform.startswith("win") and get_platform(env) == "win-arm64":
        return ["win_arm64"]

    return []


def archs_to_tags(archs: list[str]) -> list[str]:
    """
    Convert a list of architectures to a list of tags (e.g. "universal2").
    """
    if sys.platform.startswith("darwin") and set(archs) == {"arm64", "x86_64"}:
        return ["universal2"]
    return archs


def _warn_macos_arch_mismatch(cmake_path: Path, *, explicit_arch: bool) -> None:
    """
    Warn when CMake is about to build an x86_64 extension that the running
    arm64 (Apple Silicon) interpreter cannot import (#1167).

    CMake only gained Apple Silicon host detection in 3.19.2, the first release
    shipped as a universal binary. An older, x86_64-only CMake runs under
    Rosetta, sees the host as x86_64, and builds x86_64 extensions; importing
    one under an arm64 interpreter then fails with an "incompatible
    architecture" error. Skipped if the architecture was pinned explicitly
    (ARCHFLAGS / CMAKE_OSX_ARCHITECTURES), which is a deliberate cross-compile.
    """
    if (
        not explicit_arch
        and platform.machine() == "arm64"
        and _macos_binary_is_x86(cmake_path)
    ):
        logger.warning(
            "CMake ({}) is an x86_64-only binary and will build x86_64 "
            "extensions, but this is an arm64 (Apple Silicon) interpreter, so "
            "the result will fail to import. Use CMake >= 3.19.2, or set "
            "ARCHFLAGS / CMAKE_OSX_ARCHITECTURES to cross-compile on purpose.",
            cmake_path,
        )


def _filter_env_cmake_args(env_cmake_args: list[str]) -> Generator[str, None, None]:
    """
    Filter out CMake arguments that are not supported from CMAKE_ARGS.
    """

    unsupported_args = ("-DCMAKE_BUILD_TYPE", "-DCMAKE_INSTALL_PREFIX")

    for arg in env_cmake_args:
        if arg.startswith(unsupported_args):
            logger.warning("Unsupported CMAKE_ARGS ignored: {}", arg)
        else:
            yield arg


def get_cmake_args_from_settings(
    settings: ScikitBuildSettings, env: Mapping[str, str]
) -> list[str]:
    """
    Get CMake args from the settings and environment (settings ``cmake.args``
    plus the filtered ``CMAKE_ARGS`` environment variable).
    """
    # Adding CMake arguments set as environment variable
    # (needed e.g. to build for ARM OSX on conda-forge)
    env_cmake_args: list[str] = list(
        filter(None, shlex.split(env.get("CMAKE_ARGS", "")))
    )

    if env_cmake_args:
        logger.debug("Env CMAKE_ARGS: {}", env_cmake_args)

    return [*settings.cmake.args, *_filter_env_cmake_args(env_cmake_args)]


def set_environment_from_settings(
    env: dict[str, str], settings: ScikitBuildSettings
) -> None:
    """
    Apply the ``tool.scikit-build.env`` table to ``env`` (mutated in place).

    Each entry is resolved against ``env`` and written back unless it is already
    set (``setdefault`` semantics), with ``force = true`` overriding. Entries
    that resolve to nothing are skipped.
    """
    for name, value in settings.env.items():
        resolved = value.resolve(env)
        if resolved is None:
            continue
        if value.force or name not in env:
            env[name] = resolved


def _sanitize_path(path: Any) -> list[Path]:
    # This handles classes like:
    # MultiplexedPath from importlib.resources.readers (3.11+)
    # MultiplexedPath from importlib.readers (3.10)
    # MultiplexedPath from importlib_resources.readers
    if hasattr(path, "_paths"):
        # pylint: disable-next=protected-access
        return [Path(os.fspath(p)) for p in path._paths]

    return [Path(os.fspath(path))]


@dataclasses.dataclass
class Builder:
    settings: ScikitBuildSettings
    config: CMaker

    def __post_init__(self) -> None:
        # Apply the user's env table before configure/build/install so it is
        # visible to all CMake subprocesses (which share ``config.env``).
        if self.settings.env:
            set_environment_from_settings(self.config.env, self.settings)

        # Export SOURCE_DATE_EPOCH so compilers that honor it (recent GCC/Clang)
        # can produce deterministic output. setdefault preserves an explicit value
        # from the environment or the user's env table.
        if self.settings.wheel.reproducible:
            self.config.env.setdefault(
                "SOURCE_DATE_EPOCH", str(get_reproducible_epoch())
            )

    def get_cmake_args(self) -> list[str]:
        """
        Get CMake args from the settings and environment.
        """
        return get_cmake_args_from_settings(self.settings, self.config.env)

    def get_generator(self, *args: str) -> str | None:
        return self.config.get_generator(
            *self.get_cmake_args(), *args, defines=self.settings.cmake.define
        )

    def _get_entry_point_search_path(self, entry_point: str) -> dict[str, list[Path]]:
        """Get the search path dict from the entry points"""
        search_paths = {}
        eps = metadata.entry_points(group=entry_point)
        if eps:
            logger.debug(
                "Loading search paths {} from entry-points: {}", entry_point, len(eps)
            )
            for ep in eps:
                ep_value = _sanitize_path(resources.files(ep.load()))
                logger.debug("{}: {} -> {}", ep.name, ep.value, ep_value)
                if ep_value:
                    search_paths[ep.name] = ep_value
        return search_paths

    def configure(
        self,
        *,
        defines: Mapping[str, str | bool | Path],
        cache_entries: Mapping[str, str | Path] | None = None,
        name: str | None = None,
        version: Version | None = None,
        limited_api: bool | None = None,
        configure_args: Iterable[str] = (),
    ) -> None:
        cmake_defines = {
            k: ("TRUE" if v else "FALSE") if isinstance(v, bool) else str(v)
            for k, v in defines.items()
        }

        # Add any extra CMake modules
        self.config.module_dirs.extend(
            p
            for ep_paths in self._get_entry_point_search_path("cmake.module").values()
            for p in ep_paths
        )
        logger.debug("cmake.modules: {}", self.config.module_dirs)

        # Add any extra CMake prefixes
        self.config.prefix_dirs.extend(
            p
            for ep_paths in self._get_entry_point_search_path("cmake.prefix").values()
            for p in ep_paths
        )
        logger.debug("cmake.prefix: {}", self.config.prefix_dirs)

        # Add all CMake roots
        # TODO: Check for unique uppercase names
        self.config.prefix_roots.update(self._get_entry_point_search_path("cmake.root"))
        logger.debug("cmake.root: {}", self.config.prefix_roots)

        # Add site-packages to the prefix path for CMake
        site_packages = Path(sysconfig.get_path("purelib"))
        if self.settings.search.site_packages:
            self.config.prefix_dirs.append(site_packages)
            logger.debug("SITE_PACKAGES: {}", site_packages)
            if site_packages != DIR.parent.parent:
                self.config.prefix_dirs.append(DIR.parent.parent)
                logger.debug("Extra SITE_PACKAGES: {}", DIR.parent.parent)
                logger.debug("PATH: {}", sys.path)

        # Add the FindPython backport if needed
        if self.config.cmake.version < self.settings.backport.find_python:
            fp_dir = Path(find_python.__file__).parent.resolve()
            self.config.module_dirs.append(fp_dir)
            logger.debug("FindPython backport activated at {}", fp_dir)

        current_gen = self.get_generator(*configure_args)
        local_def = set_environment_for_gen(
            current_gen,
            self.config.cmake,
            self.config.env,
            self.settings.ninja,
            env_managed_keys=self.settings.env.keys(),
        )
        cmake_defines.update(local_def)

        cache_config: dict[str, str | Path | bool] = {
            "SKBUILD": "2",
            "SKBUILD_CORE_VERSION": __version__,
        }

        if name is not None:
            canonical_name = name.replace("-", "_").replace(".", "_")
            cache_config["SKBUILD_PROJECT_NAME"] = canonical_name
        if version is not None:
            # Cap to four components so it is valid for project(VERSION ...)
            cache_config["SKBUILD_PROJECT_VERSION"] = ".".join(
                str(v) for v in version.release[:4]
            )
            cache_config["SKBUILD_PROJECT_VERSION_FULL"] = str(version)

        py_api = self.settings.wheel.py_api
        gil_disabled = bool(sysconfig.get_config_var("Py_GIL_DISABLED"))

        sabi = _SabiMode.NONE
        sabi_minor: int | None = None
        if limited_api is True:
            # Handle externally-set limited_api (e.g. from setuptools)
            if sys.implementation.name != "cpython":
                logger.info("PyPy doesn't support the Limited API, ignoring")
            elif gil_disabled:
                sabi = _SabiMode.ABI3T
            else:
                sabi = _SabiMode.ABI3
        elif limited_api is None and py_api.startswith("cp3"):
            # py-api may request abi3, abi3t, or both (e.g. "cp315.cp315t").
            # A single build produces one binary, so build the ABI matching
            # the current interpreter's GIL mode.
            parts = py_api.split(".")
            classic = next((p for p in parts if p[3:].isdigit()), None)
            ft = next((p for p in parts if p.endswith("t") and p[3:-1].isdigit()), None)
            if sys.implementation.name != "cpython":
                logger.info("py-api {} requires CPython, ignoring", py_api)
            elif gil_disabled:
                # Free-threaded stable ABI (PEP 803 / abi3t)
                if ft is None:
                    logger.info(
                        "Free-threaded Python doesn't support the classic Limited API, ignoring"
                    )
                else:
                    target_minor_version = int(ft[3:-1])
                    if target_minor_version <= sys.version_info.minor:
                        sabi = _SabiMode.ABI3T
                        sabi_minor = target_minor_version
                    else:
                        logger.info(
                            "py-api {} requires free-threaded CPython >= 3.{}, ignoring",
                            ft,
                            target_minor_version,
                        )
            # Classic stable ABI (abi3)
            elif classic is None:
                logger.info(
                    "py-api {} requires free-threaded CPython, ignoring", py_api
                )
            else:
                target_minor_version = int(classic[3:])
                if target_minor_version <= sys.version_info.minor:
                    sabi = _SabiMode.ABI3
                    sabi_minor = target_minor_version

        python_library = get_python_library(self.config.env, abi3=False)
        python_sabi_library = None
        if sabi == _SabiMode.ABI3T:
            python_sabi_library = get_python_library(self.config.env, abi3t=True)
        elif sabi == _SabiMode.ABI3:
            python_sabi_library = get_python_library(self.config.env, abi3=True)
        python_include_dir = get_python_include_dir()
        numpy_include_dir = get_numpy_include_dir()

        # Warning for CPython 3.13.4 Windows bug
        if (
            sys.implementation.name == "cpython"
            and sys.version_info[:3] == (3, 13, 4)
            and sys.platform.startswith("win32")
            and not sysconfig.get_config_var("Py_GIL_DISABLED")
        ):  # pragma: nocover
            logger.warning(
                "Python 3.13.4 on Windows is broken for building, 3.13.5 was rushed out to fix it. Use an older, newer, or free-threaded version instead."
            )

        if self.settings.cmake.python_hints:
            # Classic Find Python
            cache_config["PYTHON_EXECUTABLE"] = Path(sys.executable)
            cache_config["PYTHON_INCLUDE_DIR"] = python_include_dir
            if python_library:
                cache_config["PYTHON_LIBRARY"] = python_library

            # Modern Find Python
            for prefix in ("Python", "Python3"):
                cache_config[f"{prefix}_EXECUTABLE"] = Path(sys.executable)
                cache_config[f"{prefix}_ROOT_DIR"] = Path(sys.base_exec_prefix)
                cache_config[f"{prefix}_INCLUDE_DIR"] = python_include_dir
                cache_config[f"{prefix}_FIND_REGISTRY"] = "NEVER"
                # On Windows the library is constructed and existence-checked,
                # so this is reliable. On POSIX a library hint can break
                # FindPython (which resolves it fine on its own), so this
                # stays Windows-only.
                if python_library and sysconfig.get_platform().startswith("win"):
                    cache_config[f"{prefix}_LIBRARY"] = python_library
                if python_sabi_library and sysconfig.get_platform().startswith("win"):
                    cache_config[f"{prefix}_SABI_LIBRARY"] = python_sabi_library
                if numpy_include_dir:
                    cache_config[f"{prefix}_NumPy_INCLUDE_DIR"] = numpy_include_dir

        cache_config["SKBUILD_SOABI"] = get_soabi(
            self.config.env,
            abi3=(sabi == _SabiMode.ABI3),
            abi3t=(sabi == _SabiMode.ABI3T),
        )

        # Allow CMakeLists to detect this is supposed to be a limited ABI build
        cache_config["SKBUILD_SABI_COMPONENT"] = (
            "Development.SABIModule" if sabi != _SabiMode.NONE else ""
        )

        # Allow users to detect the version requested in settings
        if sabi != _SabiMode.NONE and sabi_minor is not None:
            cache_config["SKBUILD_SABI_VERSION"] = f"3.{sabi_minor}"
        else:
            cache_config["SKBUILD_SABI_VERSION"] = ""

        if sabi == _SabiMode.ABI3T:
            cache_config["Py_TARGET_ABI3T"] = "1"

        if cache_entries:
            cache_config.update(cache_entries)

        self.config.init_cache(cache_config)

        if sys.platform.startswith("darwin"):
            # Cross-compile support for macOS - respect ARCHFLAGS if set,
            # unless CMAKE_SYSTEM_PROCESSOR is in the cmake args (conda, #207)
            archs = get_archs(self.config.env, self.get_cmake_args())
            if archs:
                cmake_defines["CMAKE_OSX_ARCHITECTURES"] = ";".join(archs)
            else:
                explicit_arch = (
                    "CMAKE_OSX_ARCHITECTURES" in self.settings.cmake.define
                    or any(
                        "CMAKE_OSX_ARCHITECTURES" in arg
                        for arg in self.get_cmake_args()
                    )
                )
                _warn_macos_arch_mismatch(
                    self.config.cmake.cmake_path, explicit_arch=explicit_arch
                )

        # Add the pre-defined or passed CMake defines
        cmake_defines.update(self.settings.cmake.define)

        self.config.configure(
            defines=cmake_defines,
            cmake_args=[*self.get_cmake_args(), *configure_args],
            toolchain=self.settings.cmake.toolchain_file,
        )

    def build(
        self, build_args: Sequence[str], *, build_type: str | None = None
    ) -> None:
        build_tool_args = self.settings.build.tool_args
        if build_tool_args:
            build_args = [*build_args, "--", *build_tool_args]

        self.config.build(
            build_args=build_args,
            targets=self.settings.build.targets,
            verbose=self.settings.build.verbose,
            build_type=build_type,
        )

    def install(
        self, install_dir: Path | None, *, build_type: str | None = None
    ) -> None:
        """
        Install to a path.

        Warning: if a package hard-codes CMAKE_INSTALL_PREFIX in the install
        commands, this will not rewrite those; set that variable when
        configuring for maximum compatibility.
        """
        components = self.settings.install.components
        targets = self.settings.install.targets
        strip = self.settings.install.strip
        assert strip is not None
        self.config.install(
            install_dir,
            strip=strip,
            components=components,
            targets=targets,
            build_type=build_type,
        )
