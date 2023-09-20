from __future__ import annotations

__all__ = ["dynamic_metadata", "get_requires_for_dynamic_metadata"]


def __dir__() -> list[str]:
    return __all__


def dynamic_metadata(
    field: str,
    settings: dict[str, object] | None = None,
) -> str:
    # this is a classic implementation, waiting for the release of
    # vcs-versioning and an improved public interface

    if field != "version":
        msg = "Only the 'version' field is supported"
        raise ValueError(msg)

    if settings:
        msg = "No inline configuration is supported"
        raise ValueError(msg)

    from setuptools_scm import Configuration, _get_version

    config = Configuration.from_file("pyproject.toml")
    version: str = _get_version(config)

    return version


def get_requires_for_dynamic_metadata(
    _settings: dict[str, object] | None = None,
) -> list[str]:
    return ["setuptools-scm"]
