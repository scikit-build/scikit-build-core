from __future__ import annotations

from pathlib import Path

__all__ = ["dynamic_metadata"]


def dynamic_metadata(
    pyproject_dict: dict[str, object]  # noqa: ARG001
) -> dict[str, str | dict[str, str | None]]:
    # this is a classic implementation, waiting for the release of
    # vcs-versioning and an improved public interface
    from setuptools_scm import Configuration, _get_version

    config = Configuration.from_file(str(Path("pyproject.toml")))
    version: str = _get_version(config)

    return {"version": version}
