"""Format variables available in the ``pyproject.toml`` evaluation"""

from __future__ import annotations

__lazy_modules__ = {f"{__spec__.parent}.settings.skbuild_model"}

import dataclasses
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

    def __getattr__(self, attr: str) -> _AnySpecDummy:
        if attr.startswith("_"):
            raise AttributeError(attr)
        return self


# Keys in PyprojectFormatter whose values accept a format spec (e.g. ``root``)
# or attribute access (e.g. ``config_setting``).
_SPEC_TAKING_KEYS = ("root", "config_setting")


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
    """Handle ``{config_setting.a.b}`` by matching the dotted attribute chain."""

    def __init__(
        self, values: Mapping[str, str | bool | None], prefix: str = ""
    ) -> None:
        self._values = values
        self._prefix = prefix

    def __getattr__(self, attr: str) -> str | ConfigSettingResolver:
        if attr.startswith("_"):
            raise AttributeError(attr)
        name = f"{self._prefix}{attr}"
        if name in self._values:
            value = self._values[name]
            if value is None:
                msg = f"config-setting {name!r} is unset and has no default"
                raise ValueError(msg)
            if isinstance(value, bool):
                return "true" if value else "false"
            return value
        if any(k.startswith(f"{name}.") for k in self._values):
            return ConfigSettingResolver(self._values, f"{name}.")
        msg = f"config-setting {name!r} is not declared"
        raise ValueError(msg)

    # Only reached for a partial name, like {config_setting.torch}
    # pylint: disable-next=invalid-format-returned
    def __format__(self, fmt: str) -> str:
        if not self._prefix:
            msg = "config_setting needs a name, like {config_setting.a.b}"
        else:
            msg = f"config-setting {self._prefix.rstrip('.')!r} is not declared"
        raise ValueError(msg)


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
