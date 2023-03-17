from __future__ import annotations

__all__ = ["dynamic_metadata"]


def __dir__() -> list[str]:
    return __all__


def dynamic_metadata(
    pyproject_dict: dict[str, object],  # noqa: ARG001
    _config_settings: dict[str, list[str] | str] | None = None,
) -> dict[str, str | dict[str, str | None]]:
    # this is a classic implementation, waiting for the release of
    # vcs-versioning and an improved public interface
    from setuptools_scm import Configuration, _get_version

    config = Configuration.from_file("pyproject.toml")
    version: str = _get_version(config)

    return {"version": version}
