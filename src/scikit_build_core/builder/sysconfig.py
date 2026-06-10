from __future__ import annotations

import configparser
import os
import sys
import sysconfig
from pathlib import Path
from typing import TYPE_CHECKING, Literal

import packaging.tags

from .._logging import logger, rich_print

if TYPE_CHECKING:
    from collections.abc import Mapping

__all__ = [
    "get_abi_flags",
    "get_cmake_platform",
    "get_numpy_include_dir",
    "get_python_include_dir",
    "get_python_library",
    "get_soabi",
    "info_print",
]


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


def _config_var_is_set(name: str) -> bool:
    """
    Read a sysconfig flag as a boolean. The value may be an ``int``, ``None``,
    or a numeric string like ``"0"``/``"1"`` depending on platform, so plain
    ``bool()`` is unsafe (``bool("0")`` is ``True``). Numeric strings are parsed
    as integers; other non-empty strings keep their truthiness.
    """
    value = sysconfig.get_config_var(name)
    if isinstance(value, str) and value.strip().lstrip("-").isdigit():
        return int(value) != 0
    return bool(value)


def _is_debug_build() -> bool:
    """Whether the interpreter is a debug build (``pythonXY_d.lib`` on Windows)."""
    return _config_var_is_set("Py_DEBUG")


def _is_free_threaded() -> bool:
    """Whether the interpreter is free-threaded (the ``t`` ABI flag)."""
    return _config_var_is_set("Py_GIL_DISABLED")


def _windows_lib_names(*, abi3: bool, abi3t: bool) -> list[str]:
    """
    Construct the candidate Windows import-library names for the running
    interpreter, mirroring CMake's ``_PYTHON_GET_NAMES`` (FindPython
    ``Support.cmake``). Debug builds get a ``_d`` suffix (tried first), and
    free-threaded builds get a ``t`` ABI flag.
    """
    free_threaded = _is_free_threaded()
    if abi3 or abi3t:
        # Stable ABI: python3.lib, or python3t.lib on free-threaded abi3t.
        t = "t" if (abi3t and free_threaded) else ""
        base = f"python3{t}"
    else:
        t = "t" if free_threaded else ""
        base = f"python3{sys.version_info[1]}{t}"
    names = [f"{base}.lib"]
    if _is_debug_build():
        names.insert(0, f"{base}_d.lib")
    return names


def _is_dir(path: Path) -> bool:
    """``Path.is_dir()`` that treats a permission-denied probe as missing."""
    try:
        return path.is_dir()
    except PermissionError:
        return False


def get_python_library(
    env: Mapping[str, str], *, abi3: bool = False, abi3t: bool = False
) -> Path | None:
    """
    Locate the Python library to hand to CMake's FindPython. Mirrors CMake's
    approach of constructing the library name and searching a known directory
    layout under the install prefix, rather than relying on POSIX-only Makefile
    config vars (which are ``None`` on Windows). Outside the cross-compile
    branch (which trusts ``DIST_EXTRA_CONFIG``), the result is
    existence-validated; ``None`` is returned when no real file is found (the
    common, safe case on POSIX, where FindPython resolves the library itself).
    """
    # When cross-compiling, check DIST_EXTRA_CONFIG first. The cross target is
    # described entirely by the config file, so this must not consult the host
    # interpreter's GIL/debug state via _windows_lib_names.
    config_file = env.get("DIST_EXTRA_CONFIG", None)
    if config_file and Path(config_file).is_file():
        cp = configparser.ConfigParser()
        cp.read(config_file)
        result = cp.get("build_ext", "library_dirs", fallback="")
        if result:
            logger.info("Reading DIST_EXTRA_CONFIG:build_ext.library_dirs={}", result)
            minor = "" if (abi3 or abi3t) else sys.version_info[1]
            suffix = "t" if abi3t else ""
            return Path(result) / f"python3{minor}{suffix}.lib"

    names: list[str] = []
    libdirs: list[Path] = []

    # Windows: construct pythonXY[t][_d].lib (or the stable-ABI python3[t].lib)
    # and probe the base install's libs/ directory. base_exec_prefix is used,
    # not prefix/exec_prefix, because venvs lack a libs/ dir but the base
    # install (and conda env roots) have it. MinGW/MSYS2 Pythons also report
    # "win32" but ship a POSIX-style libpython, so the config-var search below
    # runs as a fallback rather than stopping here.
    if sys.platform.startswith("win"):
        names += _windows_lib_names(abi3=abi3, abi3t=abi3t)
        root = Path(sys.base_exec_prefix)
        libdirs += [d for d in (root / "libs", root / "lib") if _is_dir(d)]

    # POSIX / macOS / MinGW: use the Makefile config vars (None on Windows
    # CPython), restructured into a name x directory search. Existence-gated,
    # so cases that returned None before still return None.
    ldlibrarystr = sysconfig.get_config_var("LDLIBRARY")
    librarystr = sysconfig.get_config_var("LIBRARY")
    if abi3 or abi3t:
        if abi3t and _is_free_threaded():
            replacement = f"python3{sys.version_info[1]}t"
            target = "python3t"
        else:
            replacement = f"python3{sys.version_info[1]}"
            target = "python3"
        if ldlibrarystr is not None:
            ldlibrarystr = ldlibrarystr.replace(replacement, target)
        if librarystr is not None:
            librarystr = librarystr.replace(replacement, target)

    # A static archive is only a valid hint if the interpreter itself is a
    # static build (LDLIBRARY is the archive). Otherwise, pointing FindPython
    # at e.g. LIBPL's libpythonX.Y.a (common for python-build-standalone)
    # would be worse than no hint. MinGW's import library (.dll.a) passes
    # because its LDLIBRARY ends in .a as well.
    static_ok = bool(ldlibrarystr) and str(ldlibrarystr).endswith(".a")
    names += [
        str(n)
        for n in (ldlibrarystr, librarystr)
        if n and (static_ok or not str(n).endswith(".a"))
    ]

    libdirstr = sysconfig.get_config_var("LIBDIR")
    libplstr = sysconfig.get_config_var("LIBPL")
    framework_prefix = sysconfig.get_config_var("PYTHONFRAMEWORKPREFIX")
    multiarch: str | None = sysconfig.get_config_var("MULTIARCH")
    masd: str | None = sysconfig.get_config_var("multiarchsubdir")

    if libdirstr:
        libdir = Path(libdirstr)
        if _is_dir(libdir):
            if multiarch and masd:
                if masd.startswith(os.sep):
                    masd = masd[len(os.sep) :]
                libdir_masd = libdir / masd
                if _is_dir(libdir_masd):
                    libdirs.append(libdir_masd)
            libdirs.append(libdir)
            libdir64 = libdir.with_name("lib64")
            if libdir.name == "lib" and _is_dir(libdir64):
                libdirs.append(libdir64)
    # LIBPL is CMake's CONFIGDIR (the build-time config-* directory).
    if libplstr and _is_dir(Path(libplstr)):
        libdirs.append(Path(libplstr))
    # macOS frameworks.
    if framework_prefix and _is_dir(Path(framework_prefix)):
        libdirs.append(Path(framework_prefix))

    for libdir in libdirs:
        for name in names:
            libpath = libdir / name
            try:
                if Path(os.path.expandvars(libpath)).is_file():
                    return libpath
            except PermissionError:
                continue

    log_func = logger.warning if sys.platform.startswith("win") else logger.debug
    log_func(
        "Can't find a Python library; tried names={} in dirs={}",
        names,
        [str(d) for d in libdirs],
    )
    return None


def get_python_include_dir() -> Path:
    return Path(sysconfig.get_path("include"))


def get_host_platform() -> str:
    """
    Return a string that identifies the current platform. This mimics
    setuptools get_host_platform (without 3.8 aix compat).
    """
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


def get_soabi(
    env: Mapping[str, str], *, abi3: bool = False, abi3t: bool = False
) -> str:
    if abi3t:
        return "" if sysconfig.get_platform().startswith("win") else "abi3t"
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


def get_numpy_include_dir() -> Path | None:
    try:
        import numpy as np
    except ImportError:
        return None

    return Path(np.get_include())


def get_abi_flags() -> str:
    """
    Return the ABI flags for the current Python interpreter. Derived from
    ``packaging.tags.sys_tags()`` since that works on Windows.
    """
    abi_flags: str | None = sysconfig.get_config_var("ABIFLAGS")
    if abi_flags:
        return abi_flags

    if sys.implementation.name == "cpython" and sys.platform.startswith("win32"):
        most_compatible = next(iter(packaging.tags.sys_tags()))
        full_abi = most_compatible.abi
        vers = packaging.tags.interpreter_version()
        abi_flags = full_abi[full_abi.find(vers) + len(vers) :]
        return "".join(sorted(abi_flags))

    return ""


def info_print(
    *,
    color: Literal[
        "", "black", "red", "green", "yellow", "blue", "magenta", "cyan", "white"
    ] = "",
) -> None:
    """
    Print information about the Python environment.
    """
    rich_print(
        "{bold}Detected Python Library:",
        get_python_library(os.environ, abi3=False),
        color=color,
    )
    rich_print(
        "{bold}Detected ABI3 Python Library:",
        get_python_library(os.environ, abi3=True),
        color=color,
    )
    rich_print(
        "{bold}Detected ABI3T Python Library:",
        get_python_library(os.environ, abi3t=True),
        color=color,
    )
    rich_print(
        "{bold}Detected Python Include Directory:",
        get_python_include_dir(),
        color=color,
    )
    rich_print(
        "{bold}Detected NumPy Include Directory:",
        get_numpy_include_dir(),
        color=color,
    )
    rich_print(
        "{bold}Detected Platform:",
        get_platform(),
        color=color,
    )
    rich_print(
        "{bold}Detected SOABI:",
        get_soabi(os.environ, abi3=False),
        color=color,
    )
    rich_print(
        "{bold}Detected ABI3 SOABI:",
        get_soabi(os.environ, abi3=True),
        color=color,
    )
    rich_print(
        "{bold}Detected ABI3T SOABI:",
        get_soabi(os.environ, abi3t=True),
        color=color,
    )
    rich_print(
        "{bold}Detected ABI flags:",
        get_abi_flags(),
        color=color,
    )


if __name__ == "__main__":
    info_print()
