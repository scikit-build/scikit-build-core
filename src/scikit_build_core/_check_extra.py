from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from packaging.requirements import InvalidRequirement, Requirement
from packaging.utils import canonicalize_name

from ._compat import tomllib
from ._logging import rich_warning

if TYPE_CHECKING:
    from collections.abc import Iterable

__all__ = ["warn_missing_extra"]


def __dir__() -> list[str]:
    return __all__


def _has_extra(reqlist: Iterable[str], extra: str) -> bool:
    """Return True if scikit-build-core is required with the given extra."""
    norm_extra = canonicalize_name(extra)
    for req in reqlist:
        try:
            parsed = Requirement(req)
        except InvalidRequirement:
            continue
        if canonicalize_name(parsed.name) != "scikit-build-core":
            continue
        if parsed.marker is not None and not parsed.marker.evaluate():
            continue
        if any(canonicalize_name(e) == norm_extra for e in parsed.extras):
            return True
    return False


def warn_missing_extra(
    extra: str, *, pyproject_path: Path | str = "pyproject.toml"
) -> None:
    """
    Warn if ``scikit-build-core[{extra}]`` is missing from
    ``build-system.requires``.

    The setuptools and hatchling plugins may eventually move to separate
    packages; depending on the extra keeps the plugin's requirements installed
    if that happens.
    """
    path = Path(pyproject_path)
    if not path.is_file():
        return
    with path.open("rb") as f:
        pyproject = tomllib.load(f)
    reqlist = pyproject.get("build-system", {}).get("requires", [])
    if not _has_extra(reqlist, extra):
        rich_warning(
            f"{{bold}}scikit-build-core[{extra}]{{normal}} is not in "
            "build-system.requires. Add it to keep working if the plugin moves "
            "to a separate package in the future."
        )
