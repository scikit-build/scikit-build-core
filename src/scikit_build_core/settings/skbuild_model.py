import dataclasses
from pathlib import Path
from typing import Any, Dict, List, Literal, Optional, TypedDict, Union

from packaging.specifiers import SpecifierSet
from packaging.version import Version

from .._compat.typing import Annotated

__all__ = [
    "BackportSettings",
    "BuildSettings",
    "CMakeSettings",
    "CMakeSettingsDefine",
    "EditableSettings",
    "GenerateSettings",
    "InstallSettings",
    "LoggingSettings",
    "MessagesSettings",
    "NinjaSettings",
    "SDistSettings",
    "ScikitBuildSettings",
    "SearchSettings",
    "SettingsFieldMetadata",
    "WheelSettings",
]


def __dir__() -> List[str]:
    return __all__


class SettingsFieldMetadata(TypedDict, total=False):
    display_default: Optional[str]
    deprecated: bool


class CMakeSettingsDefine(str):
    """
    A str subtype for automatically normalizing bool and list values
    to the CMake representation in the `cmake.define` settings key.
    """

    json_schema = Union[str, bool, List[str]]

    def __new__(cls, raw: Union[str, bool, List[str]]) -> "CMakeSettingsDefine":
        def escape_semicolons(item: str) -> str:
            return item.replace(";", r"\;")

        if isinstance(raw, bool):
            value = "TRUE" if raw else "FALSE"
        elif isinstance(raw, list):
            value = ";".join(map(escape_semicolons, raw))
        else:
            value = raw

        return super().__new__(cls, value)


@dataclasses.dataclass
class CMakeSettings:
    minimum_version: Optional[Version] = dataclasses.field(
        default=None, metadata=SettingsFieldMetadata(deprecated=True)
    )
    """
    DEPRECATED in 0.8; use version instead.
    """

    version: Optional[SpecifierSet] = None
    """
    The versions of CMake to allow as a python-compatible specifier.

    If CMake is not present on the system or does not pass this specifier, it will
    be downloaded via PyPI if possible with the equivalent specifier used.

    An empty string will disable this check.

    Special cases:
      - On scikit-build-core 0.10+ ``CMakeLists.txt`` is the default value otherwise it's
        ``>=3.15``.
      - If ``CMakeLists.txt`` is passed, the ``cmake_minimum_required`` is read from the
        CMakeLists.txt file, using that as the minimum specifier. If the file fails to read,
        ``>=3.15`` is used instead.

    .. seealso::
       :confval:`ninja.version`
    """

    args: List[str] = dataclasses.field(default_factory=list)
    """
    A list of args to pass to CMake when configuring the project.

    Setting this in config or envvar will override toml.

    .. seealso::
       :confval:`cmake.define`
    """

    define: Annotated[Dict[str, CMakeSettingsDefine], "EnvVar"] = dataclasses.field(
        default_factory=dict
    )
    """
    A table of defines to pass to CMake when configuring the project. Additive.
    """

    verbose: Optional[bool] = dataclasses.field(
        default=None, metadata=SettingsFieldMetadata(deprecated=True)
    )
    """
    DEPRECATED in 0.10, use build.verbose instead.
    """

    build_type: str = "Release"
    """
    The build type to use when building the project.

    Pre-defined CMake options are: ``Debug``, ``Release``, ``RelWithDebInfo``, ``MinSizeRel``

    Custom values can also be used.
    """

    source_dir: Path = Path()
    """
    The source directory to use when building the project.

    Currently only affects the native builder (not the setuptools plugin).
    """

    targets: Optional[List[str]] = dataclasses.field(
        default=None, metadata=SettingsFieldMetadata(deprecated=True)
    )
    """
    DEPRECATED in 0.10; use build.targets instead.
    """


@dataclasses.dataclass
class SearchSettings:
    site_packages: bool = True
    """
    Add the python build environment site_packages folder to the CMake prefix paths.
    """


@dataclasses.dataclass
class NinjaSettings:
    minimum_version: Optional[Version] = dataclasses.field(
        default=None, metadata=SettingsFieldMetadata(deprecated=True)
    )
    """
    DEPRECATED in 0.8; use version instead.
    """

    version: SpecifierSet = SpecifierSet(">=1.5")
    """
    The versions of Ninja to allow.

    If Ninja is not present on the system or does not pass this specifier, it will
    be downloaded via PyPI if possible with the equivalent specifier used.

    An empty string will disable this check.

    .. seealso::
       - :confval:`cmake.version`
       - :confval:`ninja.make-fallback`
    """

    make_fallback: bool = True
    """
    Use Make as a fallback if a suitable Ninja executable is not found.

    If Make is also not available on the system, a ninja dependency is added to the
    ``build-system.requires`` according to :confval:`ninja.version`.

    .. seealso::
       :confval:`ninja.version`
    """


@dataclasses.dataclass
class LoggingSettings:
    level: Literal["NOTSET", "DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = (
        "WARNING"
    )
    """
    The logging level to display.
    """


@dataclasses.dataclass
class SDistSettings:
    include: List[str] = dataclasses.field(default_factory=list)
    """
    Files to include in the SDist even if they are skipped by default. Supports gitignore syntax.

    Always takes precedence over :confval:`sdist.exclude`

    .. seealso::
       :confval:`sdist.exclude`
    """

    exclude: List[str] = dataclasses.field(default_factory=list)
    """
    Files to exclude from the SDist even if they are included by default. Supports gitignore syntax.

    .. seealso::
       :confval:`sdist.include`
    """

    reproducible: bool = True
    """
    Try to build a reproducible distribution.

    Unix and Python 3.9+ recommended.

    ``SOURCE_DATE_EPOCH`` will be used for timestamps, or a fixed value if not set.
    """

    cmake: bool = False
    """
    If set to True, CMake will be run before building the SDist.
    """


@dataclasses.dataclass
class WheelSettings:
    packages: Optional[Union[List[str], Dict[str, str]]] = dataclasses.field(
        default=None,
        metadata=SettingsFieldMetadata(
            display_default='["src/<package>", "python/<package>", "<package>"]'
        ),
    )
    """
    A list of packages to auto-copy into the wheel.

    If this is not set, it will default to the first of ``src/<package>``, ``python/<package>``, or
    ``<package>`` if they exist.  The prefix(s) will be stripped from the
    package name inside the wheel.

    If a dict, provides a mapping of package name to source directory.
    """

    py_api: str = ""
    """
    The Python version tag used in the wheel file.

    The default (empty string) will use the default Python version.

    You can also set this to "cp38" to enable the CPython 3.8+ Stable
    ABI / Limited API (only on CPython and if the version is sufficient,
    otherwise this has no effect). Or you can set it to "py3" or "py2.py3" to
    ignore Python ABI compatibility. The ABI tag is inferred from this tag.

    This value is used to construct ``SKBUILD_SABI_COMPONENT`` CMake variable.
    """

    expand_macos_universal_tags: bool = False
    """
    Fill out extra tags that are not required.

    This adds "x86_64" and "arm64" to the list of platforms when "universal2" is used,
    which helps older Pip's (before 21.0.1) find the correct wheel.
    """

    install_dir: str = ""
    """
    The CMake install prefix relative to the platlib wheel path.

    You might set this to the package name to install everything under the package namespace
    in a pythonic design.

    The original dir is still at ``SKBUILD_PLATLIB_DIR`` (also ``SKBUILD_DATA_DIR``, etc.
    are available).

    .. warning::
       EXPERIMENTAL An absolute path will be one level higher than the platlib
       root, giving access to "/platlib", "/data", "/headers", and "/scripts".
    """

    license_files: Optional[List[str]] = None
    """
    A list of license files to include in the wheel. Supports glob patterns.

    The default is ``["LICEN[CS]E*", "COPYING*", "NOTICE*", "AUTHORS*"]``.

    .. warning::
       Must not be set if ``project.license-files`` is set.
    """

    cmake: bool = True
    """
    Run CMake as part of building the wheel.
    """

    platlib: Optional[bool] = None
    """
    Target the platlib or the purelib.

    If not set, the default is to target the platlib if :confval:`wheel.cmake` is ``true``,
    and the purelib otherwise.
    """

    exclude: List[str] = dataclasses.field(default_factory=list)
    """
    A set of patterns to exclude from the wheel.

    This is additive to the SDist exclude patterns. This applies to the final paths
    in the wheel, and can exclude files from CMake output as well.  Editable installs
    may not respect this exclusion.
    """

    build_tag: str = ""
    """
    The build tag to use for the wheel. If empty, no build tag is used.
    """


@dataclasses.dataclass
class BackportSettings:
    find_python: Version = Version("3.26.1")
    """
    If CMake is less than this value, backport a copy of FindPython.

    Set to ``0`` or an empty string to disable this.
    """


@dataclasses.dataclass
class EditableSettings:
    mode: Literal["redirect", "inplace"] = "redirect"
    """
    Select the editable mode to use. Can be "redirect" (default) or "inplace".
    """

    verbose: bool = True
    """
    Turn on verbose output for the editable mode rebuilds.
    """

    rebuild: bool = False
    """
    Rebuild the project when the package is imported.

    :confval:`build-dir` must be set.
    """


@dataclasses.dataclass
class BuildSettings:
    tool_args: List[str] = dataclasses.field(default_factory=list)
    """
    Extra args to pass directly to the builder in the build step.
    """

    targets: List[str] = dataclasses.field(default_factory=list)
    """
    The build targets to use when building the project.

    If not specified or an empty list, the default target is used.
    """

    verbose: bool = False
    """
    Verbose printout when building.

    Equivalent to ``CMAKE_VERBOSE_MAKEFILE``.
    """

    requires: List[str] = dataclasses.field(default_factory=list)
    """
    Additional ``build-system.requires``.

    Intended to be used in combination with ``overrides``.
    """


@dataclasses.dataclass
class InstallSettings:
    components: List[str] = dataclasses.field(default_factory=list)
    """
    The components to install.

    If not specified or an empty list, all default components are installed.
    """

    strip: Optional[bool] = dataclasses.field(
        default=None, metadata=SettingsFieldMetadata(display_default="true")
    )
    """
    Whether to strip the binaries.

    Equivalent to ``--strip`` in ``cmake install``.

    True for release builds (`Release` or `MinSizeRel`) on scikit-build-core 0.5+.

    .. note::
       0.5-0.10.5 also incorrectly set this for debug builds.
    """


@dataclasses.dataclass
class GenerateSettings:
    path: Path
    """
    The path (relative to platlib) for the file to generate.
    """

    template: str = ""
    """
    The template string to use for the file.

    Template style placeholders are available for all the metadata.

    Either this or :confval:`generate[].template-path` must be set.

    .. seealso::
       :confval:`generate[].template-path`
    """

    template_path: Optional[Path] = None
    """
    The path to the template file. If empty, a template must be set.

    Either this or :confval:`generate[].template` must be set.

    .. seealso::
       :confval:`generate[].template`
    """

    location: Literal["install", "build", "source"] = "install"
    """
    The place to put the generated file.

    The ``build`` directory is useful for CMake files, and the ``install`` directory is
    useful for Python files, usually. You can also write directly to the ``source``
    directory, will overwrite existing files & remember to gitignore the file.
    """


@dataclasses.dataclass
class MessagesSettings:
    """
    Settings for messages.
    """

    after_failure: str = ""
    """
    A message to print after a build failure.
    """

    after_success: str = ""
    """
    A message to print after a successful build.
    """


@dataclasses.dataclass
class ScikitBuildSettings:
    cmake: CMakeSettings = dataclasses.field(default_factory=CMakeSettings)
    ninja: NinjaSettings = dataclasses.field(default_factory=NinjaSettings)
    logging: LoggingSettings = dataclasses.field(default_factory=LoggingSettings)
    sdist: SDistSettings = dataclasses.field(default_factory=SDistSettings)
    wheel: WheelSettings = dataclasses.field(default_factory=WheelSettings)
    backport: BackportSettings = dataclasses.field(default_factory=BackportSettings)
    editable: EditableSettings = dataclasses.field(default_factory=EditableSettings)
    build: BuildSettings = dataclasses.field(default_factory=BuildSettings)
    install: InstallSettings = dataclasses.field(default_factory=InstallSettings)
    generate: List[GenerateSettings] = dataclasses.field(default_factory=list)
    messages: MessagesSettings = dataclasses.field(default_factory=MessagesSettings)
    search: SearchSettings = dataclasses.field(default_factory=SearchSettings)

    metadata: Dict[str, Dict[str, Any]] = dataclasses.field(default_factory=dict)
    """
    List dynamic metadata fields and hook locations in this table.
    """

    strict_config: bool = True
    """
    Strictly check all config options.

    If False, warnings will be printed for unknown options.

    If True, an error will be raised.
    """

    experimental: bool = False
    """
    Enable early previews of features not finalized yet.
    """

    minimum_version: Optional[Version] = dataclasses.field(
        default=None,
        metadata=SettingsFieldMetadata(
            display_default='"{version}"  # current version'
        ),
    )
    """
    If set, this will provide a method for backward compatibility.
    """

    build_dir: str = ""
    """
    The CMake build directory. Defaults to a unique temporary directory.

    This can be set to reuse the build directory from previous runs.
    """

    fail: bool = False
    """
    Immediately fail the build. This is only useful in overrides.
    """
