from __future__ import annotations

from pathlib import Path

from .._compat import tomllib

__all__ = ["dynamic_metadata"]


def __dir__() -> list[str]:
    return __all__


def dynamic_metadata(
    fields: frozenset[str],
    settings: dict[str, list[str] | str] | None = None,
) -> dict[str, str | dict[str, str | None]]:
    from hatch_fancy_pypi_readme._builder import build_text
    from hatch_fancy_pypi_readme._config import load_and_validate_config

    if fields != {"readme"}:
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

    # Version 22.3 does not have fragment support
    return {
        "readme": {
            "content-type": config.content_type,
            "text": build_text(config.fragments, config.substitutions)
            if hasattr(config, "substitutions")
            # pylint: disable-next=no-value-for-parameter
            else build_text(config.fragments),  # type: ignore[call-arg]
        }
    }


def get_requires_for_dynamic_metadata(
    _settings: dict[str, object] | None = None,
) -> list[str]:
    return ["hatch-fancy-pypi-readme>=22.3"]
