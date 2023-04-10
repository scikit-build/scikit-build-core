"""
This is the entry point for the build backend. Items in this module are designed for the build backend API.
"""


from __future__ import annotations

import sys

__all__ = [
    "build_sdist",
    "build_wheel",
    "get_requires_for_build_sdist",
    "get_requires_for_build_wheel",
    "prepare_metadata_for_build_wheel",
    "build_editable",
    "get_requires_for_build_editable",
    "prepare_metadata_for_build_editable",
]


def build_wheel(
    wheel_directory: str,
    config_settings: dict[str, list[str] | str] | None = None,
    metadata_directory: str | None = None,
) -> str:
    from .._logging import rich_print
    from ..errors import FailedLiveProcessError
    from .wheel import _build_wheel_impl

    try:
        return _build_wheel_impl(
            wheel_directory,
            config_settings,
            metadata_directory,
            editable=False,
        ).wheel_filename
    except FailedLiveProcessError as err:
        sys.stdout.flush()
        rich_print(f"\n[red bold]*** {' '.join(err.args)}", file=sys.stderr)
        raise SystemExit(1) from None


def build_editable(
    wheel_directory: str,
    config_settings: dict[str, list[str] | str] | None = None,
    metadata_directory: str | None = None,
) -> str:
    from .._logging import rich_print
    from ..errors import FailedLiveProcessError
    from .wheel import _build_wheel_impl

    try:
        return _build_wheel_impl(
            wheel_directory,
            config_settings,
            metadata_directory,
            editable=True,
        ).wheel_filename
    except FailedLiveProcessError as err:
        sys.stdout.flush()
        rich_print(f"\n[red bold]*** {' '.join(err.args)}", file=sys.stderr)
        raise SystemExit(1) from None


def prepare_metadata_for_build_wheel(
    metadata_directory: str,
    config_settings: dict[str, list[str] | str] | None = None,
) -> str:
    """Prepare metadata for building a wheel. Does not build the wheel. Returns the dist-info directory."""
    from .wheel import _build_wheel_impl

    return _build_wheel_impl(
        None, config_settings, metadata_directory, editable=False
    ).wheel_filename  # actually returns the dist-info directory


def prepare_metadata_for_build_editable(
    metadata_directory: str,
    config_settings: dict[str, list[str] | str] | None = None,
) -> str:
    """Prepare metadata for building a wheel. Does not build the wheel. Returns the dist-info directory."""

    from .wheel import _build_wheel_impl

    return _build_wheel_impl(
        None, config_settings, metadata_directory, editable=True
    ).wheel_filename  # actually returns the dist-info directory


def build_sdist(
    sdist_directory: str,
    config_settings: dict[str, list[str] | str] | None = None,
) -> str:
    from .sdist import build_sdist as skbuild_build_sdist

    return skbuild_build_sdist(sdist_directory, config_settings)


def get_requires_for_build_sdist(
    config_settings: dict[str, str | list[str]] | None = None
) -> list[str]:
    from ..builder.get_requires import GetRequires

    requires = GetRequires(config_settings)

    return [
        "pathspec",
        "pyproject_metadata",
        *requires.dynamic_metadata(),
    ]


def get_requires_for_build_wheel(
    config_settings: dict[str, str | list[str]] | None = None,
) -> list[str]:
    from ..builder.get_requires import GetRequires

    requires = GetRequires(config_settings)

    return [
        "pathspec",
        "pyproject_metadata",
        *requires.cmake(),
        *requires.ninja(),
        *requires.dynamic_metadata(),
    ]


def get_requires_for_build_editable(
    config_settings: dict[str, str | list[str]] | None = None,
) -> list[str]:
    from ..builder.get_requires import GetRequires

    requires = GetRequires(config_settings)

    return [
        "pathspec",
        "pyproject_metadata",
        *requires.cmake(),
        *requires.ninja(),
        *requires.dynamic_metadata(),
    ]
