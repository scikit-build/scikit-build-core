from __future__ import annotations

from pathlib import Path

from packaging.requirements import InvalidRequirement, Requirement
from packaging.utils import canonicalize_name

from ._compat import tomllib
from ._logging import rich_warning

TYPE_CHECKING = False
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
    extra: str, *alt_extras: str, pyproject_path: Path | str = "pyproject.toml"
) -> None:
    """
    Warn if none of ``scikit-build-core[{extra}]`` (or the ``alt_extras``
    alternatives) are in ``build-system.requires``.

    The setuptools and hatchling plugins may eventually move to separate
    packages; depending on the extra keeps the plugin's requirements installed
    if that happens. Any of the given extras satisfies the check (e.g. the
    setuptools plugin accepts both ``setuptools`` and ``wheel-free-setuptools``).
    """
    path = Path(pyproject_path)
    if not path.is_file():
        return
    with path.open("rb") as f:
        pyproject = tomllib.load(f)
    reqlist = pyproject.get("build-system", {}).get("requires", [])
    extras = (extra, *alt_extras)
    if not any(_has_extra(reqlist, e) for e in extras):
        names = " or ".join(
            f"{{bold}}scikit-build-core[{canonicalize_name(e)}]{{normal}}"
            for e in extras
        )
        rich_warning(
            f"{names} is not in build-system.requires. Add it to keep working "
            "if the plugin moves to a separate package in the future."
        )
