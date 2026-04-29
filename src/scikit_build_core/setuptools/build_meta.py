# pylint: disable=duplicate-code

from __future__ import annotations

from typing import Literal

import setuptools.build_meta
from setuptools.build_meta import (
    build_sdist,
    build_wheel,
    prepare_metadata_for_build_wheel,
)

from ..builder.get_requires import GetRequires
from ..settings.skbuild_read_settings import SettingsReader
from .build_cmake import _validate_settings

if hasattr(setuptools.build_meta, "build_editable"):

    def _validate_editable_settings(
        config_settings: dict[str, str | list[str]] | None = None,
        *,
        state: Literal["editable", "metadata_editable"] = "editable",
    ) -> None:
        settings = SettingsReader.from_file(
            "pyproject.toml",
            config_settings,
            state=state,
        ).settings
        _validate_settings(settings, editable_mode=True)

    def build_editable(
        wheel_directory: str,
        config_settings: dict[str, str | list[str]] | None = None,
        metadata_directory: str | None = None,
    ) -> str:
        _validate_editable_settings(config_settings, state="editable")
        return setuptools.build_meta.build_editable(
            wheel_directory, config_settings, metadata_directory
        )


if hasattr(setuptools.build_meta, "prepare_metadata_for_build_editable"):

    def prepare_metadata_for_build_editable(
        metadata_directory: str,
        config_settings: dict[str, str | list[str]] | None = None,
    ) -> str:
        _validate_editable_settings(config_settings, state="metadata_editable")
        return setuptools.build_meta.prepare_metadata_for_build_editable(
            metadata_directory, config_settings
        )


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


def __dir__() -> list[str]:
    return __all__


def get_requires_for_build_sdist(
    config_settings: dict[str, str | list[str]] | None = None,
) -> list[str]:
    setuptools_reqs = setuptools.build_meta.get_requires_for_build_sdist(
        config_settings
    )
    requires = GetRequires.from_config_settings(config_settings)

    # These are only injected if cmake is required for the SDist step
    cmake_requires = (
        [*requires.cmake(), *requires.ninja()] if requires.settings.sdist.cmake else []
    )
    return [*setuptools_reqs, *cmake_requires]


def get_requires_for_build_wheel(
    config_settings: dict[str, str | list[str]] | None = None,
) -> list[str]:
    requires = GetRequires.from_config_settings(config_settings)

    setuptools_reqs = setuptools.build_meta.get_requires_for_build_wheel(
        config_settings
    )

    return [*setuptools_reqs, *requires.cmake(), *requires.ninja()]


if hasattr(setuptools.build_meta, "get_requires_for_build_editable"):

    def get_requires_for_build_editable(
        config_settings: dict[str, str | list[str]] | None = None,
    ) -> list[str]:
        requires = GetRequires.from_config_settings(config_settings)
        setuptools_reqs = setuptools.build_meta.get_requires_for_build_editable(
            config_settings
        )
        return [*setuptools_reqs, *requires.cmake(), *requires.ninja()]
