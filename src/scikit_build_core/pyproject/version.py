from __future__ import annotations

import re
from collections.abc import Sequence
from pathlib import Path

from ..settings.skbuild_model import ScikitBuildSettings


def process_dynamic_version(
    settings: ScikitBuildSettings, packages: Sequence[str]
) -> str:
    """
    Process the version.
    """

    # TODO: allow fallback to normal read if not found, unless setuptools_scm already does it
    if settings.version.setuptools_scm:
        if "write_to" not in settings.version.setuptools_scm:
            raise AssertionError(
                "setuptools_scm requires write_to to be set in version.setuptools_scm"
            )
        from setuptools_scm import get_version

        version: str = get_version(**settings.version.setuptools_scm)
        return version

    if settings.version.path is None:
        assert (
            len(packages) == 1
        ), "version.path must be set if there are multiple packages"
        version_path = Path(packages[0]) / "__init__.py"
    else:
        version_path = Path(settings.version.path)

    if not version_path.exists():
        raise AssertionError(f"version.path {version_path} does not exist")

    contents = version_path.read_text(encoding="utf-8")

    match = re.search(settings.version.pattern, contents, flags=re.MULTILINE)
    if not match:
        raise ValueError(f"unable to parse the version from the file: {version_path}")

    groups = match.groupdict()
    if "version" not in groups:
        raise ValueError("no group named `version` was defined in the pattern")

    return groups["version"]
