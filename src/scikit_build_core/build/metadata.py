from __future__ import annotations

import copy
import dataclasses
from typing import TYPE_CHECKING, Any

from packaging.version import Version

from .._vendor.pyproject_metadata import StandardMetadata
from ..settings._load_provider import load_dynamic_metadata

if TYPE_CHECKING:
    from collections.abc import Mapping

    from ..settings.skbuild_model import ScikitBuildSettings

__all__ = ["get_standard_metadata"]


def __dir__() -> list[str]:
    return __all__


# If pyproject-metadata eventually supports updates, this can be simplified
def get_standard_metadata(
    pyproject_dict: Mapping[str, Any],
    settings: ScikitBuildSettings,
) -> StandardMetadata:
    new_pyproject_dict = copy.deepcopy(pyproject_dict)
    # Handle any dynamic metadata
    for field, provider, config in load_dynamic_metadata(settings.metadata):
        if provider is None:
            msg = f"{field} is missing provider"
            raise KeyError(msg)
        if field not in pyproject_dict.get("project", {}).get("dynamic", []):
            msg = f"{field} is not in project.dynamic"
            raise KeyError(msg)
        new_pyproject_dict["project"][field] = provider.dynamic_metadata(field, config)
        new_pyproject_dict["project"]["dynamic"].remove(field)

    metadata = StandardMetadata.from_pyproject(new_pyproject_dict)

    # For scikit-build-core < 0.5, we keep the normalized name for back-compat
    if settings.minimum_version is not None and settings.minimum_version < Version(
        "0.5"
    ):
        metadata = dataclasses.replace(metadata, name=metadata.canonical_name)

    # The description field is required to be one line. Instead of merging it
    # or cutting off subsequent lines (setuptools), we throw a nice error.
    # But we didn't validate before 0.9.
    if (
        settings.minimum_version is None or settings.minimum_version >= Version("0.9")
    ) and "\n" in (metadata.description or ""):
        msg = "Multiple lines in project.description are not supported; this is supposed to be a one line summary"
        raise ValueError(msg)

    return metadata
