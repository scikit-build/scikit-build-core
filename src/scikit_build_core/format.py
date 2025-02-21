"""Format variables available in the ``pyproject.toml`` evaluation"""

from __future__ import annotations

import dataclasses
import sys
from pathlib import Path
from typing import TYPE_CHECKING, TypedDict

if TYPE_CHECKING:
    from typing import Literal

    from scikit_build_core.builder.wheel_tag import WheelTag
    from scikit_build_core.settings.skbuild_model import ScikitBuildSettings

__all__ = [
    "PyprojectFormatter",
    "RootPathResolver",
    "pyproject_format",
]


def __dir__() -> list[str]:
    return __all__


class PyprojectFormatter(TypedDict, total=False):
    """Format helper for pyproject.toml.

    Stores all known variables that can be used for evaluating a formatted string
    in the pyproject.toml config file.
    """

    cache_tag: str
    wheel_tag: str
    build_type: str
    state: str
    root: RootPathResolver


def pyproject_format(
    *,
    settings: ScikitBuildSettings | None = None,
    state: (
        Literal["sdist", "wheel", "editable", "metadata_wheel", "metadata_editable"]
        | None
    ) = None,
    tags: WheelTag | None = None,
    dummy: bool = False,
) -> PyprojectFormatter | dict[str, str]:
    """Generate :py:class:`PyprojectFormatter` dictionary to use in f-string format."""
    if dummy:
        # Return a dict with all the known keys but with values replaced with dummy values
        return {key: "*" for key in PyprojectFormatter.__annotations__}
    # First set all known values
    res = PyprojectFormatter(
        cache_tag=sys.implementation.cache_tag,
        # We are assuming the Path.cwd always evaluates to the folder containing pyproject.toml
        # as part of PEP517 standard.
        root=RootPathResolver(),
    )
    # Then compute all optional keys depending on the function input
    if settings is not None:
        res["build_type"] = settings.cmake.build_type
    if tags is not None:
        res["wheel_tag"] = str(tags)
    if state is not None:
        res["state"] = state
    # Construct the final dict including the always known keys
    return res


@dataclasses.dataclass()
class RootPathResolver:
    """Handle ``{root:uri}`` like formatting similar to ``hatchling``."""

    path: Path = dataclasses.field(default_factory=Path)

    def __post_init__(self) -> None:
        self.path = self.path.resolve()

    def __format__(self, fmt: str) -> str:
        command, _, rest = fmt.partition(":")
        if command == "parent":
            parent = RootPathResolver(self.path.parent)
            return parent.__format__(rest)
        if command == "uri" and rest == "":
            return self.path.as_uri()
        if command == "" and rest == "":
            return str(self)
        msg = f"Could not handle format: {fmt}"
        raise ValueError(msg)
