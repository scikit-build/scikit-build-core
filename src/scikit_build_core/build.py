# pylint: disable=unused-argument

from __future__ import annotations

from .builder.get_requires import cmake_ninja_for_build_wheel

__all__ = [
    "build_sdist",
    "build_wheel",
    "get_requires_for_build_sdist",
    "get_requires_for_build_wheel",
]


def __dir__() -> list[str]:
    return __all__


def build_wheel(
    wheel_directory: str,
    config_settings: dict[str, list[str] | str] | None = None,
    metadata_directory: str | None = None,
) -> str:
    from .pyproject.wheel import build_wheel as skbuild_build_wheel

    return skbuild_build_wheel(wheel_directory, config_settings, metadata_directory)


def build_sdist(
    sdist_directory: str,
    config_settings: dict[str, list[str] | str] | None = None,
) -> str:
    from .pyproject.sdist import build_sdist as skbuild_build_sdist

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
    return ["distlib", "pyproject_metadata"] + cmake_ninja_for_build_wheel(
        config_settings
    )
