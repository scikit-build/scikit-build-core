from __future__ import annotations

import warnings
from typing import TYPE_CHECKING, Any

import setuptools

if TYPE_CHECKING:
    from collections.abc import Callable, Sequence

__all__ = ["setup"]


def __dir__() -> list[str]:
    return __all__


def setup(
    *,
    cmake_args: Sequence[str] = (),
    cmake_install_dir: str = "",
    cmake_source_dir: str = "",
    cmake_with_sdist: bool = False,
    cmake_languages: Sequence[str] | None = None,
    cmake_minimum_required_version: str | None = None,
    cmake_process_manifest_hook: Callable[[list[str]], list[str]] | None = None,
    cmake_install_target: str = "install",
    **kw: Any,
) -> setuptools.Distribution:
    assert not cmake_install_dir, "cmake_install_dir not supported yet"
    assert not cmake_with_sdist, "cmake_with_sdist not supported yet"
    assert cmake_process_manifest_hook is None, (
        "cmake_process_manifest_hook not supported yet"
    )
    assert cmake_install_target == "install", "cmake_install_target not supported yet"

    if cmake_languages is not None:
        warnings.warn("cmake_languages no longer has any effect", stacklevel=2)

    if cmake_minimum_required_version is not None:
        warnings.warn("Set via pyproject.toml", stacklevel=2)

    return setuptools.setup(
        cmake_source_dir=cmake_source_dir, cmake_args=cmake_args, **kw
    )
