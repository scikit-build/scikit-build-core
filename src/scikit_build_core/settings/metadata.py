from __future__ import annotations

import importlib
from typing import Any

from pyproject_metadata import StandardMetadata

from ..settings.skbuild_model import ScikitBuildSettings

__all__ = ["get_standard_metadata"]


def __dir__() -> list[str]:
    return __all__


def _load(
    mod_name: str,
    pyproject_dict: dict[str, Any],
    config_settings: dict[str, list[str] | str] | None = None,
) -> dict[str, Any]:
    return importlib.import_module(mod_name).dynamic_metadata(pyproject_dict, config_settings)  # type: ignore[no-any-return]


# If pyproject-metadata eventually supports updates, this can be simplified
def get_standard_metadata(
    pyproject_dict: dict[str, Any],
    settings: ScikitBuildSettings,
    config_settings: dict[str, list[str] | str] | None = None,
) -> StandardMetadata:
    # Handle any dynamic metadata
    for field in settings.metadata:
        if field not in pyproject_dict.get("project", {}).get("dynamic", []):
            msg = f"{field} is not in project.dynamic"
            raise KeyError(msg)

    plugins = set(settings.metadata.values())
    cached_plugins = {
        key: _load(key, pyproject_dict, config_settings) for key in plugins
    }

    for field, mod_name in settings.metadata.items():
        if field not in cached_plugins[mod_name]:
            msg = f"{field} is not provided by plugin {mod_name}"
            raise KeyError(msg)

        pyproject_dict["project"][field] = cached_plugins[mod_name][field]
        pyproject_dict["project"]["dynamic"].remove(field)

    return StandardMetadata.from_pyproject(pyproject_dict)
