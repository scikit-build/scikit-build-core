from __future__ import annotations

from . import _require_field

TYPE_CHECKING = False
if TYPE_CHECKING:
    from collections.abc import Mapping
    from typing import Any

__all__ = ["Provider", "dynamic_metadata", "get_requires_for_dynamic_metadata"]


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
    version: str | None
    try:
        version = _get_version(config, force_write_version_files=True)
    except TypeError:  # setuptools_scm < 8
        version = _get_version(config)

    if version is None:
        msg = (
            f"setuptools-scm was unable to detect version for {config.absolute_root}.\n\n"
            "Make sure you're either building from a fully intact git repository "
            "or PyPI tarballs. Most other sources (such as GitHub's tarballs, a "
            "git checkout without the .git folder) don't contain the necessary "
            "metadata and will not work.\n\n"
            "For example, if you're using pip, instead of "
            "https://github.com/user/proj/archive/master.zip "
            "use git+https://github.com/user/proj.git#egg=proj"
        )

        raise ValueError(msg)

    return version


def get_requires_for_dynamic_metadata(
    _settings: dict[str, object] | None = None,
) -> list[str]:
    return ["setuptools-scm"]


class Provider:
    """New-style (dynamic-metadata 0.3) wrapper around :func:`dynamic_metadata`.

    Registered as the ``scikit_build_core.metadata.setuptools_scm`` entry point;
    only the ``version`` field is produced, so ``field`` defaults to ``"version"``.
    """

    @staticmethod
    def dynamic_metadata(
        settings: Mapping[str, Any],
        _project: Mapping[str, Any],
    ) -> dict[str, Any]:
        field, rest = _require_field(settings, default="version")
        return {field: dynamic_metadata(field, rest)}

    @staticmethod
    def get_requires_for_dynamic_metadata(settings: Mapping[str, Any]) -> list[str]:
        return get_requires_for_dynamic_metadata(dict(settings))
