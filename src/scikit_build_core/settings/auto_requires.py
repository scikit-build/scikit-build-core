from __future__ import annotations

from typing import TYPE_CHECKING

from packaging.requirements import Requirement
from packaging.utils import canonicalize_name
from packaging.version import Version

if TYPE_CHECKING:
    from collections.abc import Iterable

    from packaging.specifiers import Specifier

__all__ = ["get_min_requires"]


def __dir__() -> list[str]:
    return __all__


def get_min_requires(package: str, reqlist: Iterable[str]) -> Version | None:
    """
    Read the build requirements from a pyproject.toml file
    and return the minimum version required for the given package.
    Returns None if no minimum version is discovered.
    """

    norm_package = canonicalize_name(package)

    requires = [Requirement(req) for req in reqlist]

    versions = (
        min_from_spec(v)
        for req in requires
        if canonicalize_name(req.name) == norm_package
        and (req.marker is None or req.marker.evaluate())
        for v in req.specifier
    )
    return min((v for v in versions if v is not None), default=None)


def min_from_spec(spec: Specifier) -> Version | None:
    """
    Return the minimum version from a specifier.

    Returns None if no minimum version is discovered.
    ">" technically doesn't include the minimum, but any
    larger version is acceptable, so it is treated as the
    minimum.
    """

    if spec.operator in {">=", ">", "==", "~="}:
        return Version(spec.version)
    return None
