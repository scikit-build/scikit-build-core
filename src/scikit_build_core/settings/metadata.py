from __future__ import annotations

import pathlib
import warnings

from pyproject_metadata import StandardMetadata

from .._compat import importlib, tomllib
from ..settings.skbuild_model import ScikitBuildSettings

__all__ = ["setuptools_scm_version", "fancy_pypi_readme", "get_standard_metadata"]


def __dir__() -> list[str]:
    return __all__


def setuptools_scm_version(pyproject_path: pathlib.Path) -> str:
    from setuptools_scm import Configuration, _get_version

    config = Configuration.from_file(str(pyproject_path))
    version: str = _get_version(config)

    return version


def fancy_pypi_readme(pyproject_path: pathlib.Path) -> str | dict[str, str | None]:
    from hatch_fancy_pypi_readme._builder import build_text
    from hatch_fancy_pypi_readme._config import load_and_validate_config

    with pyproject_path.open("rb") as ft:
        pyproject = tomllib.load(ft)

    config = load_and_validate_config(
        pyproject["tool"]["hatch"]["metadata"]["hooks"]["fancy-pypi-readme"]
    )

    return {
        "content-type": config.content_type,
        "text": build_text(config.fragments, config.substitutions),
    }


def get_standard_metadata(
    pyproject_path: pathlib.Path, settings: ScikitBuildSettings
) -> StandardMetadata:
    with pyproject_path.open("rb") as ft:
        pyproject = tomllib.load(ft)
    metadata = StandardMetadata.from_pyproject(pyproject)

    # handle any dynamic metadata
    # start by collecting all the scikit-build entrypoints
    eps: importlib.metadata.EntryPoints = importlib.metadata.entry_points(
        group="skbuild"
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
            pyproject["project"][field] = ep.load()(pyproject_path)
            pyproject["project"]["dynamic"].remove(field)

    # if pyproject-metadata supports updates, we won't need this line anymore
    metadata = StandardMetadata.from_pyproject(pyproject)
    return metadata
