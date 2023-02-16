from __future__ import annotations

import warnings
from pathlib import Path
from typing import Any

from pyproject_metadata import StandardMetadata

from .._compat import importlib
from ..settings.skbuild_model import ScikitBuildSettings

__all__ = ["setuptools_scm_version", "fancy_pypi_readme", "get_standard_metadata"]


def __dir__() -> list[str]:
    return __all__


def setuptools_scm_version(_pyproject_dict: dict[str, Any]) -> str:
    # this is a placeholder version of this function, waiting for the release
    # of vcs-versioning and an improved public interface
    from setuptools_scm import Configuration, _get_version

    config = Configuration.from_file(str(Path("pyproject.toml")))
    version: str = _get_version(config)

    return version


def fancy_pypi_readme(pyproject_dict: dict[str, Any]) -> str | dict[str, str | None]:
    from hatch_fancy_pypi_readme._builder import build_text
    from hatch_fancy_pypi_readme._config import load_and_validate_config

    config = load_and_validate_config(
        pyproject_dict["tool"]["hatch"]["metadata"]["hooks"]["fancy-pypi-readme"]
    )

    return {
        "content-type": config.content_type,
        "text": build_text(config.fragments, config.substitutions),
    }


def get_standard_metadata(
    pyproject_dict: dict[str, Any], settings: ScikitBuildSettings
) -> StandardMetadata:
    metadata = StandardMetadata.from_pyproject(pyproject_dict)

    # handle any dynamic metadata
    # start by collecting all the scikit-build entrypoints
    eps: importlib.metadata.EntryPoints = importlib.metadata.entry_points(
        group="scikit_build.metadata"
    )
    for field, ep_name in settings.metadata.items():
        if field not in metadata.dynamic:
            msg = f"{field} is not in project.dynamic"
            raise KeyError(msg)
        try:
            ep = eps[ep_name]
        except KeyError:
            warnings.warn(
                f"could not find requested entrypoint {ep_name} for field {field}"
            )
        else:
            # would be better to update the metadata directly but this is
            # currently not supported by pyproject_metadata
            # metadata.__setattr__(field, ep.load()(pyproject_path)
            pyproject_dict["project"][field] = ep.load()(pyproject_dict)
            pyproject_dict["project"]["dynamic"].remove(field)

    # if pyproject-metadata supports updates, we won't need this line anymore
    metadata = StandardMetadata.from_pyproject(pyproject_dict)
    return metadata
