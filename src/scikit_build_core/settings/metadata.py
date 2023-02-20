from __future__ import annotations

import importlib
from typing import Any

from pyproject_metadata import StandardMetadata

from ..settings.skbuild_model import ScikitBuildSettings

__all__ = ["get_standard_metadata"]


def __dir__() -> list[str]:
    return __all__


def _load(mod_name: str, pyproject_dict: dict[str, Any]) -> dict[str, Any]:
    return importlib.import_module(mod_name).dynamic_metadata(pyproject_dict)  # type: ignore[no-any-return]


def get_standard_metadata(
    pyproject_dict: dict[str, Any], settings: ScikitBuildSettings
) -> StandardMetadata:
    metadata = StandardMetadata.from_pyproject(pyproject_dict)

    # handle any dynamic metadata
    for field in settings.metadata:
        if field not in metadata.dynamic:
            msg = f"{field} is not in project.dynamic"
            raise KeyError(msg)

    plugins = set(settings.metadata.values())
    cached_plugins = {key: _load(key, pyproject_dict) for key in plugins}

    for field, mod_name in settings.metadata.items():
        # would be better to update the metadata directly but this is
        # currently not supported by pyproject_metadata
        # metadata.__setattr__(field, ep.load()(pyproject_path)
        if field in cached_plugins[mod_name]:
            pyproject_dict["project"][field] = cached_plugins[mod_name][field]
            pyproject_dict["project"]["dynamic"].remove(field)
        else:
            msg = f"{field} is not provided by plugin {mod_name}"
            raise KeyError(msg)

    # if pyproject-metadata supports updates, we won't need this line anymore
    metadata = StandardMetadata.from_pyproject(pyproject_dict)
    return metadata
