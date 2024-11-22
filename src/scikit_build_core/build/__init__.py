"""
This is the entry point for the build backend. Items in this module are designed for the build backend API.
"""

from __future__ import annotations

import sys

from .._compat import tomllib

__all__ = [
    "build_editable",
    "build_sdist",
    "build_wheel",
    "get_requires_for_build_editable",
    "get_requires_for_build_sdist",
    "get_requires_for_build_wheel",
    "prepare_metadata_for_build_editable",
    "prepare_metadata_for_build_wheel",
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
        rich_print("\n{bold}***", *err.args, color="red", file=sys.stderr)
        if err.msg:
            rich_print(err.msg)
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
        rich_print("\n{bold}***", *err.args, color="red", file=sys.stderr)
        if err.msg:
            rich_print(err.msg)
        raise SystemExit(1) from None


def _has_safe_metadata() -> bool:
    try:
        with open("pyproject.toml", "rb") as f:  # noqa: PTH123
            pyproject = tomllib.load(f)
    except FileNotFoundError:
        return True

    overrides = pyproject.get("tool", {}).get("scikit-build", {}).get("overrides", [])
    for override in overrides:
        if_override = override.get("if", {})
        if "failed" in if_override or "failed" in if_override.get("any", {}):
            return False

    return True


if _has_safe_metadata():

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

    __all__ += [
        "prepare_metadata_for_build_editable",
        "prepare_metadata_for_build_wheel",
    ]


def build_sdist(
    sdist_directory: str,
    config_settings: dict[str, list[str] | str] | None = None,
) -> str:
    from .._logging import rich_print
    from ..errors import FailedLiveProcessError
    from .sdist import build_sdist as skbuild_build_sdist

    try:
        return skbuild_build_sdist(sdist_directory, config_settings)
    except FailedLiveProcessError as err:
        sys.stdout.flush()
        rich_print("\n{bold}***", *err.args, color="red", file=sys.stderr)
        if err.msg:
            rich_print(err.msg)
        raise SystemExit(1) from None


def get_requires_for_build_sdist(
    config_settings: dict[str, str | list[str]] | None = None,
) -> list[str]:
    from ..builder.get_requires import GetRequires

    requires = GetRequires.from_config_settings(config_settings)

    # These are only injected if cmake is required for the SDist step
    cmake_requires = (
        [*requires.cmake(), *requires.ninja()] if requires.settings.sdist.cmake else []
    )

    return [
        *cmake_requires,
        *requires.dynamic_metadata(),
    ]


def get_requires_for_build_wheel(
    config_settings: dict[str, str | list[str]] | None = None,
) -> list[str]:
    from ..builder.get_requires import GetRequires

    requires = GetRequires.from_config_settings(config_settings)

    # These are only injected if cmake is required for the wheel step
    cmake_requires = (
        [*requires.cmake(), *requires.ninja()] if requires.settings.wheel.cmake else []
    )

    return [
        *cmake_requires,
        *requires.dynamic_metadata(),
    ]


def get_requires_for_build_editable(
    config_settings: dict[str, str | list[str]] | None = None,
) -> list[str]:
    from ..builder.get_requires import GetRequires

    requires = GetRequires.from_config_settings(config_settings)

    # These are only injected if cmake is required for the wheel step
    cmake_requires = (
        [*requires.cmake(), *requires.ninja()] if requires.settings.wheel.cmake else []
    )

    return [
        *cmake_requires,
        *requires.dynamic_metadata(),
    ]
