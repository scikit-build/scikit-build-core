from __future__ import annotations

import configparser
import os
import sys
import sysconfig
from collections.abc import Mapping
from pathlib import Path

from .._logging import logger

__all__ = ["get_python_include_dir", "get_python_library", "get_cmake_platform"]


TARGET_TO_PLAT = {
    "x86": "win32",
    "x64": "win-amd64",
    "arm": "win-arm32",
    "arm64": "win-arm64",
}

PLAT_TO_CMAKE = {
    "win32": "Win32",
    "win-amd64": "x64",
    "win-arm32": "ARM",
    "win-arm64": "ARM64",
}


def __dir__() -> list[str]:
    return __all__


def get_python_library(env: Mapping[str, str], *, abi3: bool = False) -> Path | None:
    # When cross-compiling, check DIST_EXTRA_CONFIG first
    config_file = env.get("DIST_EXTRA_CONFIG", None)
    if config_file and Path(config_file).is_file():
        cp = configparser.ConfigParser()
        cp.read(config_file)
        result = cp.get("build_ext", "library_dirs", fallback="")
        if result:
            logger.info("Reading DIST_EXTRA_CONFIG:build_ext.library_dirs={}", result)
            minor = "" if abi3 else sys.version_info[1]
            return Path(result) / f"python3{minor}.lib"

    libdirstr = sysconfig.get_config_var("LIBDIR")
    ldlibrarystr = sysconfig.get_config_var("LDLIBRARY")
    libdir: Path | None = libdirstr and Path(libdirstr)
    ldlibrary: Path | None = ldlibrarystr and Path(ldlibrarystr)
    multiarch: str | None = sysconfig.get_config_var("MULTIARCH")
    masd: str | None = sysconfig.get_config_var("multiarchsubdir")

    if libdir and ldlibrary:
        try:
            libdir_is_dir = libdir.is_dir()
        except PermissionError:
            return None
        if libdir_is_dir:
            if multiarch and masd:
                if masd.startswith(os.sep):
                    masd = masd[len(os.sep) :]
                libdir_masd = libdir / masd
                if libdir_masd.is_dir():
                    libdir = libdir_masd
            libpath = libdir / ldlibrary
            if Path(os.path.expandvars(libpath)).is_file():
                return libpath
            logger.warning("libdir/ldlibrary: {} is not a real file!", libpath)
        else:
            logger.warning("libdir: {} is not a directory", libdir)

    framework_prefix = sysconfig.get_config_var("PYTHONFRAMEWORKPREFIX")
    if framework_prefix and Path(framework_prefix).is_dir() and ldlibrary:
        libpath = Path(framework_prefix) / ldlibrary
        if libpath.is_file():
            return libpath

    logger.warning(
        "Can't find a Python library, got libdir={}, ldlibrary={}, multiarch={}, masd={}",
        libdir,
        ldlibrary,
        multiarch,
        masd,
    )
    return None


def get_python_include_dir() -> Path:
    return Path(sysconfig.get_path("include"))


def get_host_platform() -> str:
    """
    Return a string that identifies the current platform. This mimics
    setuptools get_host_platform (without 3.8 aix compat).
    """

    if sys.version_info < (3, 8) and os.name == "nt":
        if "(arm)" in sys.version.lower():
            return "win-arm32"
        if "(arm64)" in sys.version.lower():
            return "win-arm64"

    return sysconfig.get_platform()


def get_platform(env: Mapping[str, str] | None = None) -> str:
    """
    Return the Python platform name for a platform, respecting VSCMD_ARG_TGT_ARCH.
    """
    if env is None:
        env = os.environ
    if sysconfig.get_platform().startswith("win"):
        if "VSCMD_ARG_TGT_ARCH" in env:
            logger.debug(
                "Selecting {} or {} due to VSCMD_ARG_TARGET_ARCH",
                TARGET_TO_PLAT.get(env["VSCMD_ARG_TGT_ARCH"]),
                get_host_platform(),
            )
            return TARGET_TO_PLAT.get(env["VSCMD_ARG_TGT_ARCH"]) or get_host_platform()
        if "arm64" in env.get("SETUPTOOLS_EXT_SUFFIX", "").lower():
            logger.debug("Windows ARM targeted via SETUPTOOLS_EXT_SUFFIX")
            return "win-arm64"
    return get_host_platform()


def get_cmake_platform(env: Mapping[str, str] | None) -> str:
    """
    Return the CMake platform name for a platform, respecting VSCMD_ARG_TGT_ARCH.
    """
    plat = get_platform(env)
    return PLAT_TO_CMAKE.get(plat, plat)


def get_soabi(env: Mapping[str, str], *, abi3: bool = False) -> str:
    if abi3:
        return "" if sysconfig.get_platform().startswith("win") else "abi3"

    # Cross-compile support
    setuptools_ext_suffix = env.get("SETUPTOOLS_EXT_SUFFIX", "")
    if setuptools_ext_suffix:
        return setuptools_ext_suffix.rsplit(".", 1)[0].lstrip(".")

    if sys.version_info < (3, 8, 7):
        # See https://github.com/python/cpython/issues/84006
        import distutils.sysconfig  # pylint: disable=deprecated-module

        ext_suffix = distutils.sysconfig.get_config_var("EXT_SUFFIX")
    else:
        ext_suffix = sysconfig.get_config_var("EXT_SUFFIX")

    assert isinstance(ext_suffix, str)
    return ext_suffix.rsplit(".", 1)[0].lstrip(".")
