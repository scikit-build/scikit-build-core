"""Format variables available in the ``pyproject.toml`` evaluation"""

from __future__ import annotations

import dataclasses
import sys
import typing
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
    """Tag used by the import machinery in the filenames of cached modules, i.e. ``sys.implementation.cache_tag``."""
    wheel_tag: str
    """The tags as computed for the wheel."""
    build_type: str
    """Build type passed as ``cmake.build_type``."""
    state: Literal["sdist", "wheel", "editable", "metadata_wheel", "metadata_editable"]
    """The state of the build."""
    root: RootPathResolver
    """Root path of the current project."""


class _AnySpecDummy:
    """A dummy value whose ``__format__`` accepts any spec and returns ``"*"``.

    Used for dummy-mode formatting of keys that take a format spec (e.g.
    ``{root:uri}``), so that ``"{root:uri}".format(...)`` does not raise.
    """

    def __format__(self, fmt: str) -> str:
        return "*"

    def __str__(self) -> str:
        return "*"


# Keys in PyprojectFormatter whose values accept a format spec (e.g. ``root``).
_SPEC_TAKING_KEYS = ("root",)


@typing.overload
def pyproject_format(
    *,
    settings: ScikitBuildSettings,
    state: Literal["sdist", "wheel", "editable", "metadata_wheel", "metadata_editable"]
    | None = ...,
    tags: WheelTag | None = ...,
) -> PyprojectFormatter: ...


@typing.overload
def pyproject_format(*, dummy: Literal[True]) -> dict[str, str]: ...


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
        res_dummy: dict[str, object] = dict.fromkeys(
            PyprojectFormatter.__annotations__, "*"
        )
        # Keys that accept a format spec (e.g. ``{root:uri}``) must use a value
        # whose ``__format__`` accepts any spec, otherwise dummy formatting of a
        # build-dir like ``{root:uri}`` raises ValueError.
        for key in _SPEC_TAKING_KEYS:
            res_dummy[key] = _AnySpecDummy()
        return typing.cast("dict[str, str]", res_dummy)

    assert settings is not None
    # First set all known values
    res = PyprojectFormatter(
        cache_tag=sys.implementation.cache_tag,
        # We are assuming the Path.cwd always evaluates to the folder containing pyproject.toml
        # as part of PEP517 standard.
        root=RootPathResolver(),
        build_type=settings.cmake.build_type,
    )
    # Then compute all optional keys depending on the function input
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

    def __str__(self) -> str:
        return str(self.path)

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
