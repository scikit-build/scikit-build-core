from __future__ import annotations

from pathlib import Path
from typing import Any

from .._compat import tomllib

__all__ = [
    "dynamic_metadata",
    "dynamic_requires_needs",
    "get_requires_for_dynamic_metadata",
]


def __dir__() -> list[str]:
    return __all__


def dynamic_metadata(
    field: str,
    settings: dict[str, list[str] | str],
    metadata: dict[str, Any],
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

    if hasattr(config, "substitutions"):
        try:
            # We don't have access to the version at this point
            text = build_text(
                config.fragments, config.substitutions, version=metadata["version"]
            )
        except TypeError:
            # Version 23.2.0 and before don't have a version field
            # pylint: disable-next=no-value-for-parameter
            text = build_text(config.fragments, config.substitutions)
    else:
        # Version 22.3 does not have fragment support
        # pylint: disable-next=no-value-for-parameter
        text = build_text(config.fragments)  # type: ignore[call-arg]

    return {
        "content-type": config.content_type,
        "text": text,
    }


def get_requires_for_dynamic_metadata(
    _settings: dict[str, object] | None = None,
) -> list[str]:
    return ["hatch-fancy-pypi-readme>=22.3"]


def dynamic_requires_needs(
    _field: str,
    _settings: dict[str, object],
) -> list[str]:
    return ["version"]
