"""Format variables available in the ``pyproject.toml`` evaluation"""

from __future__ import annotations

__lazy_modules__ = {"itertools", f"{__spec__.parent}.settings.skbuild_model"}

import dataclasses
import itertools
import sys
import typing
from pathlib import Path
from typing import TypedDict

from .settings.skbuild_model import normalize_build_types

TYPE_CHECKING = False
if TYPE_CHECKING:
    from collections.abc import Mapping
    from typing import Literal

    from scikit_build_core.builder.wheel_tag import WheelTag
    from scikit_build_core.settings.skbuild_model import ScikitBuildSettings

__all__ = [
    "ConfigSettingResolver",
    "PyprojectFormatter",
    "RootPathResolver",
    "build_dir_exclude_patterns",
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
    config_setting: ConfigSettingResolver
    """Declared config-settings (``tool.scikit-build.config-setting``), by name, e.g. ``build-dir = "build/{config_setting.torch.variant}"``. Booleans format as ``true``/``false``. An undeclared or unset setting is an error."""


class _AnySpecDummy:
    """A dummy value whose ``__format__`` accepts any spec and returns ``"*"``.

    Used for dummy-mode formatting of keys that take a format spec (e.g.
    ``{root:uri}``), so that ``"{root:uri}".format(...)`` does not raise.
    """

    def __format__(self, fmt: str) -> str:
        return "*"

    def __str__(self) -> str:
        return "*"


class _ConfigSettingDummy:
    """Dummy for ``config_setting``: any attribute chain formats as ``text``."""

    def __init__(self, text: str) -> None:
        self._text = text

    # Setting segments can be any name, including ones like ``_text``.
    def __getattribute__(self, attr: str) -> _ConfigSettingDummy:
        return self

    def __format__(self, fmt: str) -> str:
        return str(self)

    def __str__(self) -> str:
        text: str = object.__getattribute__(self, "_text")
        return text

    __repr__ = __str__


# Stands for a config-setting value in a dummy-formatted build-dir.
_CONFIG_SETTING_MARK = "\0"


def build_dir_exclude_patterns(build_dir: str) -> list[str]:
    """
    Gitignore patterns that match every directory ``build_dir`` can format to.

    A config-setting value can contain path separators, so each one gets a
    pattern for a single component and a pattern for several.
    """
    if not build_dir:
        return []
    dummy = pyproject_format(dummy=True)
    dummy["config_setting"] = typing.cast(
        "str", _ConfigSettingDummy(_CONFIG_SETTING_MARK)
    )
    parts = build_dir.format(**dummy).split(_CONFIG_SETTING_MARK)
    return [
        parts[0] + "".join(g + p for g, p in zip(globs, parts[1:], strict=True))
        for globs in itertools.product(("*", "*/**/*"), repeat=len(parts) - 1)
    ]


@typing.overload
def pyproject_format(
    *,
    settings: ScikitBuildSettings,
    state: Literal["sdist", "wheel", "editable", "metadata_wheel", "metadata_editable"]
    | None = ...,
    tags: WheelTag | None = ...,
    name: str | None = ...,
    build_dir: Path | None = ...,
    config_settings: Mapping[str, str | bool | None] | None = ...,
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
    name: str | None = None,
    build_dir: Path | None = None,
    config_settings: Mapping[str, str | bool | None] | None = None,
    dummy: bool = False,
) -> PyprojectFormatter | dict[str, str]:
    """Generate :py:class:`PyprojectFormatter` dictionary to use in f-string format."""
    if dummy:
        # Return a dict with all the known keys but with values replaced with dummy values
        res_dummy: dict[str, object] = dict.fromkeys(
            PyprojectFormatter.__annotations__, "*"
        )
        # ``{root:uri}`` needs a value whose ``__format__`` accepts any spec.
        res_dummy["root"] = _AnySpecDummy()
        res_dummy["config_setting"] = _ConfigSettingDummy("*")
        return typing.cast("dict[str, str]", res_dummy)

    assert settings is not None
    # First set all known values
    res = PyprojectFormatter(
        cache_tag=sys.implementation.cache_tag,
        # We are assuming the Path.cwd always evaluates to the folder containing pyproject.toml
        # as part of PEP517 standard.
        root=RootPathResolver(),
        build_type=normalize_build_types(settings.cmake.build_type)[0],
        config_setting=ConfigSettingResolver(config_settings or {}),
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
    # Construct the final dict including the always known keys
    return res


class ConfigSettingResolver:
    """Handle ``{config_setting.a.b}`` by collecting the dotted attribute chain.

    The value is read only when the complete name is known, on format or
    conversion (``!s``, ``!r``, ``!a``).
    """

    def __init__(self, values: Mapping[str, str | bool | None], name: str = "") -> None:
        self._values = values
        self._name = name

    # Not __getattr__: a segment can be any name, including ``_values``.
    def __getattribute__(self, attr: str) -> ConfigSettingResolver:
        values = object.__getattribute__(self, "_values")
        name = object.__getattribute__(self, "_name")
        return ConfigSettingResolver(values, f"{name}.{attr}" if name else attr)

    def __str__(self) -> str:
        values: Mapping[str, str | bool | None] = object.__getattribute__(
            self, "_values"
        )
        name: str = object.__getattribute__(self, "_name")
        if not name:
            msg = "config_setting needs a name, like {config_setting.a.b}"
            raise ValueError(msg)
        if name not in values:
            msg = f"config-setting {name!r} is not declared"
            raise ValueError(msg)
        value = values[name]
        if value is None:
            msg = f"config-setting {name!r} is unset and has no default"
            raise ValueError(msg)
        if isinstance(value, bool):
            return "true" if value else "false"
        return value

    def __repr__(self) -> str:
        return repr(str(self))

    def __format__(self, fmt: str) -> str:
        return format(str(self), fmt)


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
