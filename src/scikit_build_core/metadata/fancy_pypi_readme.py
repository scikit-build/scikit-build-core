from __future__ import annotations

__lazy_modules__ = {
    f"{(__spec__.parent or '').rsplit('.', 1)[0]}._compat",
    "pathlib",
    "typing",
}

from pathlib import Path
from typing import Any

from .._compat import tomllib
from . import _require_field

TYPE_CHECKING = False
if TYPE_CHECKING:
    from collections.abc import Mapping

__all__ = [
    "Provider",
    "dynamic_metadata",
    "get_requires_for_dynamic_metadata",
]


def __dir__() -> list[str]:
    return __all__


def dynamic_metadata(
    field: str,
    settings: dict[str, list[str] | str],
    project: Mapping[str, Any],
) -> str | dict[str, str]:
    from hatch_fancy_pypi_readme._builder import build_text
    from hatch_fancy_pypi_readme._config import load_and_validate_config

    if field != "readme":
        msg = "Only the 'readme' field is supported"
        raise ValueError(msg)

    if settings:
        msg = "No inline configuration is supported"
        raise ValueError(msg)

    with Path("pyproject.toml").open("rb") as f:
        pyproject_dict = tomllib.load(f)

    config = load_and_validate_config(
        pyproject_dict["tool"]["hatch"]["metadata"]["hooks"]["fancy-pypi-readme"]
    )

    try:
        text = build_text(
            config.fragments,
            getattr(config, "substitutions", []),
            version=project["version"],
            package_name=project["name"],
        )
    except TypeError:
        # hatch-fancy-pypi-readme >=25.1 required for package name
        text = build_text(
            config.fragments,
            getattr(config, "substitutions", []),
            version=project["version"],
        )

    return {
        "content-type": config.content_type,
        "text": text,
    }


def get_requires_for_dynamic_metadata(
    _settings: dict[str, object] | None = None,
) -> list[str]:
    return ["hatch-fancy-pypi-readme>=23.2"]


class Provider:
    """New-style (dynamic-metadata 0.3) wrapper around :func:`dynamic_metadata`.

    Registered as the ``scikit_build_core.metadata.fancy_pypi_readme`` entry
    point; only the ``readme`` field is produced, so ``field`` defaults to
    ``"readme"``.
    """

    @staticmethod
    def dynamic_metadata(
        settings: Mapping[str, Any],
        project: Mapping[str, Any],
    ) -> dict[str, Any]:
        field, rest = _require_field(settings, default="readme")
        return {field: dynamic_metadata(field, rest, project)}

    @staticmethod
    def get_requires_for_dynamic_metadata(settings: Mapping[str, Any]) -> list[str]:
        return get_requires_for_dynamic_metadata(dict(settings))
