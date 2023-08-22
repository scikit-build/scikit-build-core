from __future__ import annotations

from typing import TYPE_CHECKING, Any

from packaging.version import Version
from pyproject_metadata import StandardMetadata

from ._load_provider import load_dynamic_metadata

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
    new_pyproject_dict = dict(pyproject_dict)
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
    # pyproject-metadata normalizes the name - see https://github.com/FFY00/python-pyproject-metadata/pull/65
    # For scikit-build-core 0.5+, we keep the un-normalized name, and normalize it when using it for filenames
    if settings.minimum_version is None or settings.minimum_version >= Version("0.5"):
        metadata.name = new_pyproject_dict["project"]["name"]
    return metadata
