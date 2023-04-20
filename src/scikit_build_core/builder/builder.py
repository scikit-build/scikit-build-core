from __future__ import annotations

import dataclasses
import re
import sys
import sysconfig
from collections.abc import Mapping, Sequence
from pathlib import Path

from packaging.version import Version

from .. import __version__
from .._compat.importlib import metadata, resources
from .._logging import logger
from ..cmake import CMaker
from ..resources import find_python
from ..settings.skbuild_model import ScikitBuildSettings
from .generator import set_environment_for_gen
from .sysconfig import get_platform, get_python_include_dir, get_python_library

__all__: list[str] = ["Builder", "get_archs", "archs_to_tags"]

DIR = Path(__file__).parent.resolve()


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
        archs = re.findall(r"-arch (\S+)", env.get("ARCHFLAGS", ""))
        return archs
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


@dataclasses.dataclass
class Builder:
    settings: ScikitBuildSettings
    config: CMaker

    def get_cmake_args(self) -> list[str]:
        """
        Get CMake args from the settings and environment.
        """
        # Adding CMake arguments set as environment variable
        # (needed e.g. to build for ARM OSX on conda-forge)
        env_cmake_args = filter(None, self.config.env.get("CMAKE_ARGS", "").split(" "))

        return [*self.settings.cmake.args, *env_cmake_args]

    def configure(
        self,
        *,
        defines: Mapping[str, str],
        cache_entries: Mapping[str, str | Path] | None = None,
        name: str | None = None,
        version: Version | None = None,
        limited_abi: bool | None = None,
    ) -> None:
        cmake_defines = dict(defines)

        # Add any extra CMake modules
        eps = metadata.entry_points(group="cmake.module")
        self.config.module_dirs.extend(resources.files(ep.load()) for ep in eps)

        # Add any extra CMake prefixes
        eps = metadata.entry_points(group="cmake.prefix")
        self.config.prefix_dirs.extend(resources.files(ep.load()) for ep in eps)

        # Add site-packages to the prefix path for CMake
        site_packages = Path(sysconfig.get_path("purelib"))
        self.config.prefix_dirs.append(site_packages)
        logger.debug("SITE_PACKAGES: {}", site_packages)
        if site_packages != DIR.parent.parent:
            self.config.prefix_dirs.append(DIR.parent.parent)
            logger.debug("Extra SITE_PACKAGES: {}", site_packages)

        # Add the FindPython backport if needed
        fp_backport = self.settings.backport.find_python
        if fp_backport and self.config.cmake.version < Version(fp_backport):
            fp_dir = Path(find_python.__file__).parent.resolve()
            self.config.module_dirs.append(fp_dir)
            logger.debug("FindPython backport activated at {}", fp_dir)

        local_def = set_environment_for_gen(
            self.config.cmake, self.config.env, self.settings.ninja
        )
        cmake_defines.update(local_def)

        cache_config: dict[str, str | Path] = {
            "SKBUILD": "2",
            "SKBUILD_CORE_VERSION": __version__,
        }

        if name is not None:
            canonical_name = name.replace("-", "_").replace(".", "_")
            cache_config["SKBUILD_PROJECT_NAME"] = canonical_name
        if version is not None:
            cache_config["SKBUILD_PROJECT_VERSION"] = str(version)

        if limited_abi is None:
            limited_abi = self.settings.wheel.py_api.startswith("cp3")

        python_library = get_python_library(self.config.env, abi3=limited_abi)
        python_include_dir = get_python_include_dir()

        # Classic Find Python
        cache_config["PYTHON_EXECUTABLE"] = sys.executable
        cache_config["PYTHON_INCLUDE_DIR"] = python_include_dir
        if python_library:
            cache_config["PYTHON_LIBRARY"] = python_library

        # Modern Find Python
        for prefix in ("Python", "Python3"):
            cache_config[f"{prefix}_EXECUTABLE"] = sys.executable
            cache_config[f"{prefix}_ROOT_DIR"] = sys.prefix
            cache_config[f"{prefix}_INCLUDE_DIR"] = python_include_dir
            cache_config[f"{prefix}_FIND_REGISTRY"] = "NEVER"
            # FindPython may break if this is set - only useful on Windows
            if python_library and sysconfig.get_platform().startswith("win"):
                cache_config[f"{prefix}_LIBRARY"] = python_library

        if limited_abi:
            cache_config["SKBUILD_SOABI"] = (
                "" if sysconfig.get_platform().startswith("win") else "abi3"
            )
        else:
            # Workaround for bug in PyPy and packaging that is not handled in CMake
            # According to PEP 3149, SOABI and EXT_SUFFIX are interchangeable (and
            # the latter is much more likely to be correct as it is used elsewhere)
            if sys.version_info < (3, 8, 7):
                # See https://github.com/python/cpython/issues/84006
                import distutils.sysconfig  # pylint: disable=deprecated-module

                ext_suffix = distutils.sysconfig.get_config_var("EXT_SUFFIX")
            else:
                ext_suffix = sysconfig.get_config_var("EXT_SUFFIX")
            assert isinstance(ext_suffix, str)
            cache_config["SKBUILD_SOABI"] = ext_suffix.rsplit(".", 1)[0].lstrip(".")

        if cache_entries:
            cache_config.update(cache_entries)

        self.config.init_cache(cache_config)

        if sys.platform.startswith("darwin"):
            # Cross-compile support for macOS - respect ARCHFLAGS if set
            archs = get_archs(self.config.env)
            if archs:
                cmake_defines["CMAKE_OSX_ARCHITECTURES"] = ";".join(archs)

        # Add the pre-defined or passed CMake defines
        cmake_defines.update(self.settings.cmake.define)

        self.config.configure(
            defines=cmake_defines,
            cmake_args=self.get_cmake_args(),
        )

    def build(self, build_args: list[str]) -> None:
        self.config.build(build_args=build_args, verbose=self.settings.cmake.verbose)

    def install(self, install_dir: Path) -> None:
        self.config.install(install_dir)
