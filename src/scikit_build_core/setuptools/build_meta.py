from __future__ import annotations

from ..builder.get_requires import cmake_ninja_for_build_wheel

__all__ = [
    "prepare_metadata_for_build_wheel",
    "build_wheel",
    "build_sdist",
    "get_requires_for_build_sdist",
    "get_requires_for_build_wheel",
]


def __dir__() -> list[str]:
    return __all__


def get_requires_for_build_sdist(
    # pylint: disable-next=unused-argument
    config_settings: dict[str, str | list[str]]
    | None = None
) -> list[str]:
    return ["setuptools"]


def get_requires_for_build_wheel(
    config_settings: dict[str, str | list[str]] | None = None
) -> list[str]:
    return ["setuptools", "wheel"] + cmake_ninja_for_build_wheel(config_settings)


def build_sdist(
    sdist_directory: str,
    config_settings: dict[str, str | list[str]] | None = None,
) -> str:
    import setuptools.build_meta

    return setuptools.build_meta.build_sdist(  # type: ignore[no-any-return]
        sdist_directory, config_settings
    )


def build_wheel(
    wheel_directory: str,
    config_settings: dict[str, str | list[str]] | None = None,
    metadata_directory: str | None = None,
) -> str:
    import setuptools.build_meta

    return setuptools.build_meta.build_wheel(  # type: ignore[no-any-return]
        wheel_directory, config_settings, metadata_directory
    )


def prepare_metadata_for_build_wheel(
    metadata_directory: str,
    config_settings: dict[str, str | list[str]] | None = None,
) -> str:
    import setuptools.build_meta

    return setuptools.build_meta.prepare_metadata_for_build_wheel(  # type: ignore[no-any-return]
        metadata_directory, config_settings
    )
