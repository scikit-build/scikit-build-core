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
