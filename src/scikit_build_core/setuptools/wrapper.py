from __future__ import annotations

import warnings
from pathlib import Path
from typing import TYPE_CHECKING, Any, cast

import setuptools

if TYPE_CHECKING:
    from collections.abc import Callable, Sequence

from .._compat.typing import TypeVar
from .build_cmake import (
    WRAPPER_CLASSIC_LAYOUT_COMPAT,
    WRAPPER_CMAKE_INSTALL_DIR_COMPAT,
)

__all__ = ["setup"]


def __dir__() -> list[str]:
    return __all__


_DistributionT = TypeVar(
    "_DistributionT",
    bound="setuptools._distutils.dist.Distribution",
    default=setuptools.Distribution,
)


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
    distclass: type[_DistributionT] = setuptools.Distribution,  # type: ignore[assignment]
    **kw: Any,
) -> _DistributionT:
    assert not cmake_with_sdist, "cmake_with_sdist not supported yet"
    assert cmake_install_target == "install", "cmake_install_target not supported yet"

    if cmake_languages is not None:
        warnings.warn("cmake_languages no longer has any effect", stacklevel=2)

    if cmake_minimum_required_version is not None:
        warnings.warn("Set via pyproject.toml", stacklevel=2)

    # Classic scikit-build builds projects without a CMakeLists.txt as plain
    # setuptools projects. A nonexistent cmake_source_dir still errors via the
    # cmake_source_dir keyword validator below.
    source_dir = Path(cmake_source_dir or ".")
    if source_dir.is_dir() and not source_dir.joinpath("CMakeLists.txt").is_file():
        print("skipping skbuild (no CMakeLists.txt found)", flush=True)  # noqa: T201
        return setuptools.setup(distclass=distclass, **kw)

    distribution_class = cast(
        "type[_DistributionT]",
        type(
            "DistributionClass",
            (distclass,),
            {
                WRAPPER_CLASSIC_LAYOUT_COMPAT: True,
                WRAPPER_CMAKE_INSTALL_DIR_COMPAT: True,
            },
        ),
    )

    if isinstance(cmake_args, str):
        msg = "cmake_args must be a list, not a string"
        raise TypeError(msg)

    return setuptools.setup(
        cmake_source_dir=cmake_source_dir,
        cmake_with_sdist=cmake_with_sdist,
        cmake_args=list(cmake_args),
        cmake_install_dir=cmake_install_dir,
        cmake_process_manifest_hook=cmake_process_manifest_hook,
        distclass=distribution_class,
        **kw,
    )
