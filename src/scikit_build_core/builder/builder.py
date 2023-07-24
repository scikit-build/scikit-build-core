from __future__ import annotations

import dataclasses
import hashlib
import os
import re
import sys
import sysconfig
import tarfile
import tempfile
from collections.abc import Iterable, Mapping, Sequence
from pathlib import Path
from typing import BinaryIO

from packaging.version import Version

from .. import __version__
from .._compat.importlib import metadata, resources
from .._logging import logger
from ..cmake import CMaker
from ..resources import find_python
from ..settings.skbuild_model import ScikitBuildSettings
from .generator import set_environment_for_gen
from .sysconfig import (
    get_platform,
    get_python_include_dir,
    get_python_library,
    get_soabi,
)
from .wheel_tag import WheelTag

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


@dataclasses.dataclass(init=False)
class BuildEnvArchive:
    _archive_file: BinaryIO
    hash: hashlib._Hash

    def __init__(self, env_dir: Path) -> None:
        self._archive_file = tempfile.TemporaryFile(prefix="build-env-archive-", suffix=".tar")  # type: ignore[assignment]

        # Rewrite environment path to be relative to root
        # Example:
        #       /tmp/pip-build-env-pklovjqz/overlay/lib/python3.11/site-packages
        #   is rewritten into
        #       tmp/pip-build-env-pklovjqz/overlay/lib/python3.11/site-packages
        prefix = Path(env_dir)
        prefix = prefix.relative_to(prefix.root)

        def ext_filter(ti: tarfile.TarInfo) -> tarfile.TarInfo | None:
            pname = Path(ti.name)

            if ti.type is tarfile.LNKTYPE:
                logger.warning(
                    "Unexpected link inside build environment archive (path={})", pname
                )
            elif (
                ti.type is not tarfile.REGTYPE
                and ti.type is not tarfile.AREGTYPE
                and ti.type is not tarfile.DIRTYPE
            ):
                logger.warning(
                    "Unexpected file type inside build environment archive (path={})",
                    pname,
                )

            # Rewrite name to be relative to site-packages inside the build environment
            ti.name = str(pname.relative_to(prefix))

            # FIXME: __pycache__ files don't have consistent hashes - why?
            if "__pycache__" in ti.name:
                return None

            # Reset mtime to zero
            # This is safe (regarding build tool out-of-date detection)
            # since the resulting archive is content-addressed through its hash
            ti.mtime = 0

            return ti

        with tarfile.open(
            fileobj=self._archive_file, mode="x", dereference=True
        ) as dir_tar:
            dir_tar.add(env_dir, filter=ext_filter)

        self._archive_file.flush()

        archive_len = self._archive_file.tell()
        self._archive_file.seek(0)

        self.hash = hashlib.file_digest(self._archive_file, hashlib.sha256)  # type: ignore[attr-defined]
        self._archive_file.seek(0)

        logger.debug(
            "created build env archive len={} sha256={}",
            archive_len,
            self.hash.hexdigest(),
        )

    def extract(self, destination: Path) -> None:
        self._archive_file.seek(0)
        with tarfile.open(fileobj=self._archive_file, mode="r") as dir_tar:
            dir_tar.extractall(path=destination)

        # Reset atime/mtime of the destination directory
        # Otherwise CMake would consider the directory out of date
        # FIXME: Apparently not necessary?
        # os.utime(destination, times=(0,0))


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

    # FIXME: Proper setting for build env dir
    def _build_dir(self) -> Path:
        tags = WheelTag.compute_best(
            archs_to_tags(get_archs(os.environ)),
            self.settings.wheel.py_api,
            expand_macos=self.settings.wheel.expand_macos_universal_tags,
        )

        assert self.settings.build_dir is not None
        # A build dir can be specified, otherwise use a temporary directory
        build_dir = Path(
            self.settings.build_dir.format(
                cache_tag=sys.implementation.cache_tag,
                wheel_tag=str(tags),
            )
        )
        logger.info("Build directory: {}", build_dir.resolve())

        return build_dir.resolve()

    def _build_env_cache_dir(self, hash: hashlib._Hash) -> Path:
        base_dir = self._build_dir()
        base_dir = base_dir.with_name(base_dir.name + "-build-env-cache")
        return base_dir / hash.hexdigest()

    def configure(
        self,
        *,
        defines: Mapping[str, str],
        cache_entries: Mapping[str, str | Path] | None = None,
        name: str | None = None,
        version: Version | None = None,
        limited_abi: bool | None = None,
        configure_args: Iterable[str] = (),
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

        if self.settings.cache_build_env:
            if not self.settings.experimental:
                msg = "Experimental features must be enabled to use build environment caching"
                raise AssertionError(msg)

            archive = BuildEnvArchive(DIR.parent.parent)
            targettree = self._build_env_cache_dir(archive.hash)
            archive.extract(targettree)
            self.config.prefix_dirs.append(targettree)

        elif site_packages != DIR.parent.parent:
            self.config.prefix_dirs.append(DIR.parent.parent)
            logger.debug("Extra SITE_PACKAGES: {}", DIR.parent.parent)

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

        cache_config: dict[str, str | Path | bool] = {
            "SKBUILD": "2",
            "SKBUILD_CORE_VERSION": __version__,
        }

        if name is not None:
            canonical_name = name.replace("-", "_").replace(".", "_")
            cache_config["SKBUILD_PROJECT_NAME"] = canonical_name
        if version is not None:
            cache_config["SKBUILD_PROJECT_VERSION"] = str(version)

        if limited_abi is None:
            if self.settings.wheel.py_api.startswith("cp3"):
                target_minor_version = int(self.settings.wheel.py_api[3:])
                limited_abi = target_minor_version <= sys.version_info.minor
            else:
                limited_abi = False

        python_library = get_python_library(self.config.env, abi3=False)
        python_sabi_library = (
            get_python_library(self.config.env, abi3=True) if limited_abi else None
        )
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
            if python_sabi_library and sysconfig.get_platform().startswith("win"):
                cache_config[f"{prefix}_SABI_LIBRARY"] = python_sabi_library

        cache_config["SKBUILD_SOABI"] = get_soabi(self.config.env, abi3=limited_abi)

        # Allow CMakeLists to detect this is supposed to be a limited ABI build
        cache_config["SKBUILD_SABI_COMPONENT"] = (
            "Development.SABIModule" if limited_abi else ""
        )

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
            cmake_args=[*self.get_cmake_args(), *configure_args],
        )

    def build(self, build_args: list[str]) -> None:
        self.config.build(
            build_args=build_args,
            targets=self.settings.cmake.targets,
            verbose=self.settings.cmake.verbose,
        )

    def install(self, install_dir: Path) -> None:
        components = self.settings.install.components
        strip = self.settings.install.strip
        assert strip is not None
        self.config.install(install_dir, strip=strip, components=components)
