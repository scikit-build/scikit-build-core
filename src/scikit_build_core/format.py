"""Format variables available in the ``pyproject.toml`` evaluation"""

from __future__ import annotations

__lazy_modules__ = {
    "re",
    "string",
    f"{__spec__.parent}._logging",
    f"{__spec__.parent}.settings.skbuild_model",
}

import dataclasses
import re
import string
import sys
import typing
from pathlib import Path
from typing import TypedDict

from ._logging import rich_error
from .settings.skbuild_model import normalize_build_types

TYPE_CHECKING = False
if TYPE_CHECKING:
    from collections.abc import Iterator, Mapping
    from typing import Literal

    from scikit_build_core.builder.wheel_tag import WheelTag
    from scikit_build_core.settings.skbuild_model import ScikitBuildSettings

__all__ = [
    "PyprojectFormatter",
    "RootPathResolver",
    "format_template",
    "pyproject_format",
    "template_fields",
    "template_glob",
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
    name: str
    """The normalized project name (canonicalized per :pep:`503`, then ``-`` replaced by ``_``), matching the wheel/sdist filename. Handy to disambiguate a shared ``build-dir`` across a workspace, e.g. ``build-dir = "build/{name}/{wheel_tag}"``. Not available while resolving ``build.requires``, since metadata is not read yet at that point."""
    wheel_tag: str
    """The tags as computed for the wheel."""
    build_type: str
    """Build type passed as ``cmake.build_type``."""
    state: Literal["sdist", "wheel", "editable", "metadata_wheel", "metadata_editable"]
    """The state of the build."""
    root: RootPathResolver
    """Root path of the current project."""
    build_dir: str
    """The resolved ``build-dir``. Only available in :confval:`editable.rebuild-dir`, e.g. ``rebuild-dir = "{build_dir}/install/{wheel_tag}"`` keeps the install tree next to the build tree when ``SKBUILD_BUILD_DIR`` moves it."""


def format_template(template: str, values: Mapping[str, object], *, key: str) -> str:
    """Format the ``key`` setting; exit with a clear error on a bad placeholder."""
    try:
        return template.format(**values)
    except KeyError as err:
        rich_error("{key}: unknown placeholder {err}", key=key, err=err)
    except (AttributeError, IndexError, ValueError) as err:
        rich_error("{key}: {err}", key=key, err=err)


def template_fields(template: str) -> Iterator[tuple[str, str | None]]:
    """
    Yield the literal text and the placeholder name of each part of a template.

    The name does not have the index or attribute. It is None for a part with
    no placeholder.
    """
    for literal, field, _, _ in string.Formatter().parse(template):
        name = None if field is None else re.split(r"[.\[]", field, maxsplit=1)[0]
        yield literal, name


def template_glob(template: str, *, key: str) -> str:
    """
    Make a glob from the ``key`` setting, with ``*`` for each placeholder.

    The index, attribute, conversion and format spec of a placeholder are not
    applied, because the result on the real value is not known.
    """
    try:
        return "".join(
            literal + ("" if name is None else "*")
            for literal, name in template_fields(template)
        )
    except ValueError as err:
        rich_error("{key}: {err}", key=key, err=err)


def pyproject_format(
    *,
    settings: ScikitBuildSettings,
    state: (
        Literal["sdist", "wheel", "editable", "metadata_wheel", "metadata_editable"]
        | None
    ) = None,
    tags: WheelTag | None = None,
    name: str | None = None,
    build_dir: Path | None = None,
) -> PyprojectFormatter:
    """
    Generate :py:class:`PyprojectFormatter` dictionary to use in f-string format.

    The result also has the ``format-keys`` of ``settings``.
    """
    # First set all known values
    res = PyprojectFormatter(
        cache_tag=sys.implementation.cache_tag,
        # We are assuming the Path.cwd always evaluates to the folder containing pyproject.toml
        # as part of PEP517 standard.
        root=RootPathResolver(),
        build_type=normalize_build_types(settings.cmake.build_type)[0],
    )
    # Then compute all optional keys depending on the function input
    if tags is not None:
        res["wheel_tag"] = str(tags)
    if state is not None:
        res["state"] = state
    if name is not None:
        res["name"] = name
    if build_dir is not None:
        res["build_dir"] = str(build_dir.resolve())
    # A format key overrides a built-in key, so a new built-in key does not
    # change a project that already uses the name.
    return typing.cast("PyprojectFormatter", {**res, **settings.format_keys})


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
