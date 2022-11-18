from __future__ import annotations

import os
import platform
import sys

from .. import __version__

__all__ = ["print_debug_failure"]


def __dir__() -> list[str]:
    return __all__


def get_glibc_version_confstr() -> str | None:
    try:
        return os.confstr("CS_GNU_LIBC_VERSION")
    except (ValueError, OSError):
        return None


def get_glibc_version_ctypes() -> str | None:
    try:
        import ctypes

        process_namespace = ctypes.CDLL(None)
        gnu_get_libc_version = process_namespace.gnu_get_libc_version
        gnu_get_libc_version.restype = ctypes.c_char_p
        glibc_version: str | bytes = gnu_get_libc_version()
        if not isinstance(glibc_version, str):
            glibc_version = glibc_version.decode("ascii")
        return glibc_version
    except (ValueError, OSError, ImportError, AttributeError):
        return None


def print_debug_failure(msg: str) -> None:
    """Values available:

    * python: python version
    * platform: platform name
    * machine: machine arch
    * platinfo: platform info (glibc or macOS version)
    * executable: Python path
    * bits: 32 or 64
    * __version__: scikit-build version
    """

    if sys.platform.startswith("linux"):
        glibc_version = get_glibc_version_confstr() or get_glibc_version_ctypes()
        platinfo = (
            "linux glibc: {glibc_version}"
            if glibc_version
            else "linux (unknown glibc version)"
        )
    elif sys.platform.startswith("darwin"):
        platinfo = f"macos: {platform.mac_ver()[0]}"
    elif sys.platform.startswith("win32"):
        platinfo = "windows"
    else:
        platinfo = "unknown"

    fmt_msg = msg.format(
        python=".".join(str(v) for v in sys.version_info[:3]),
        platform=platform.platform(),
        machine=platform.machine(),
        bits=64 if sys.maxsize > 2**32 else 32,
        executable=sys.executable,
        platinfo=platinfo,
        __version__=__version__,
    )

    print(fmt_msg, file=sys.stderr)
