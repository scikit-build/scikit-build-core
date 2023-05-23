from __future__ import annotations

import setuptools.build_meta
from setuptools.build_meta import (
    build_sdist,
    build_wheel,
    prepare_metadata_for_build_wheel,
)

if hasattr(setuptools.build_meta, "build_editable"):
    from setuptools.build_meta import build_editable

if hasattr(setuptools.build_meta, "prepare_metadata_for_build_editable"):
    from setuptools.build_meta import (
        prepare_metadata_for_build_editable,
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
    config_settings: dict[str, str | list[str]] | None = None
) -> list[str]:
    setuptools_reqs = setuptools.build_meta.get_requires_for_build_sdist(
        config_settings
    )
    return [*setuptools_reqs]


def get_requires_for_build_wheel(
    config_settings: dict[str, str | list[str]] | None = None
) -> list[str]:
    from ..builder.get_requires import GetRequires

    requires = GetRequires(config_settings)

    setuptools_reqs = setuptools.build_meta.get_requires_for_build_wheel(
        config_settings
    )

    return [*setuptools_reqs, *requires.cmake(), *requires.ninja()]


if hasattr(setuptools.build_meta, "get_requires_for_build_editable"):

    def get_requires_for_build_editable(
        config_settings: dict[str, str | list[str]] | None = None
    ) -> list[str]:
        from ..builder.get_requires import GetRequires

        requires = GetRequires(config_settings)
        setuptools_reqs = setuptools.build_meta.get_requires_for_build_editable(
            config_settings
        )
        return [*setuptools_reqs, *requires.cmake(), *requires.ninja()]
