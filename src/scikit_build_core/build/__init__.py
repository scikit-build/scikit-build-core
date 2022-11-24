# pylint: disable=unused-argument

from __future__ import annotations

import sys

__all__ = [
    "build_sdist",
    "build_wheel",
    "get_requires_for_build_sdist",
    "get_requires_for_build_wheel",
]


def build_wheel(
    wheel_directory: str,
    config_settings: dict[str, list[str] | str] | None = None,
    metadata_directory: str | None = None,
) -> str:
    from .._logging import rich_print
    from ..errors import FailedLiveProcessError
    from .wheel import build_wheel as skbuild_build_wheel

    try:
        return skbuild_build_wheel(wheel_directory, config_settings, metadata_directory)
    except FailedLiveProcessError as err:
        sys.stdout.flush()
        rich_print(f"\n[red bold]*** {' '.join(err.args)}", file=sys.stderr)
        raise SystemExit(1) from None


def build_sdist(
    sdist_directory: str,
    config_settings: dict[str, list[str] | str] | None = None,
) -> str:
    from .sdist import build_sdist as skbuild_build_sdist

    return skbuild_build_sdist(sdist_directory, config_settings)


def get_requires_for_build_sdist(
    # pylint: disable-next=unused-argument
    config_settings: dict[str, str | list[str]]
    | None = None
) -> list[str]:
    return ["pathspec", "pyproject_metadata"]


def get_requires_for_build_wheel(
    config_settings: dict[str, str | list[str]] | None = None,
) -> list[str]:
    from ..builder.get_requires import cmake_ninja_for_build_wheel

    return ["distlib", "pathspec", "pyproject_metadata"] + cmake_ninja_for_build_wheel(
        config_settings
    )
