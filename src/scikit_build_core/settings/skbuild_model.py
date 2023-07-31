import dataclasses
from typing import Any, Dict, List, Optional

__all__ = [
    "BackportSettings",
    "CMakeSettings",
    "EditableSettings",
    "InstallSettings",
    "LoggingSettings",
    "NinjaSettings",
    "SDistSettings",
    "ScikitBuildSettings",
    "WheelSettings",
]


def __dir__() -> List[str]:
    return __all__


@dataclasses.dataclass
class NinjaSettings:
    minimum_version: str = "1.5"
    """
    The minimum version of Ninja to use. If Ninja is older than this, it will
    be upgraded via PyPI if possible. An empty string will disable this check.
    """

    make_fallback: bool = True
    """
    If make is present, do not add ninja if missing.
    """


@dataclasses.dataclass
class CMakeSettings:
    minimum_version: str = "3.15"
    """
    The minimum version of CMake to use. If CMake is older than this, it will
    be upgraded via PyPI if possible. An empty string will disable this check.
    """

    args: List[str] = dataclasses.field(default_factory=list)
    """
    A list of args to pass to CMake when configuring the project.
    """

    define: Dict[str, str] = dataclasses.field(default_factory=dict)
    """
    A table of defines to pass to CMake when configuring the project. Additive.
    """

    verbose: bool = False
    """
    Verbose printout when building
    """

    build_type: str = "Release"
    """
    The build type to use when building the project.
    Valid options are: "Debug", "Release", "RelWithDebInfo", "MinSizeRel",
    "", etc.
    """

    source_dir: str = ""
    """
    The source directory to use when building the project. Currently only
    affects the native builder (not the setuptools plugin).
    """

    targets: List[str] = dataclasses.field(default_factory=list)
    """
    The build targets to use when building the project. Empty builds the
    default target.
    """


@dataclasses.dataclass
class LoggingSettings:
    level: str = "WARNING"
    """
    The logging level to display.
    """


@dataclasses.dataclass
class SDistSettings:
    include: List[str] = dataclasses.field(default_factory=list)
    """
    Files to include in the SDist even if they are skipped by default.
    """

    exclude: List[str] = dataclasses.field(default_factory=list)
    """
    Files to exclude from the SDist even if they are included by default.
    """

    reproducible: bool = True
    """
    If set to True, try to build a reproducible distribution.
    ``SOURCE_DATE_EPOCH`` will be used for timestamps, or a fixed value if not set.
    """


@dataclasses.dataclass
class WheelSettings:
    packages: Optional[List[str]] = None
    """
    A list of packages to auto-copy into the wheel. If this is None, it will
    default to the first of ``src/<package>`` or ``<package>`` if they exist.
    The prefix(s) will be stripped from the package name inside the wheel.
    """

    py_api: str = ""
    """
    The Python tags. The default (empty string) will use the default
    Python version. You can also set this to "cp37" to enable the CPython
    3.7+ Stable ABI / Limited API (only on CPython and if the version is
    sufficient, otherwise this has no effect). Or you can set it to "py3"
    or "py2.py3" to ignore Python ABI compatibility. For the stable ABI,
    the CMake variable SKBUILD_SOABI will be set to abi3 on Unix-like systems
    (empty on Windows). FindPython doesn't have a way to target python3.dll
    instead of python3N.dll, so this is harder to use on Windows.
    The ABI tag is inferred from this tag.
    """

    expand_macos_universal_tags: bool = False
    """
    Fill out extra tags that are not required. This adds "x86_64" and "arm64"
    to the list of platforms when "universal2" is used, which helps older
    Pip's (before 21.0.1) find the correct wheel.
    """

    install_dir: str = ""
    """
    The install directory for the wheel. This is relative to the platlib root.
    EXPERIMENTAL: An absolute path will be one level higher than the platlib
    root, giving access to "/platlib", "/data", "/headers", and "/scripts".
    """

    license_files: List[str] = dataclasses.field(
        default_factory=lambda: ["LICEN[CS]E*", "COPYING*", "NOTICE*", "AUTHORS*"]
    )
    """
    A list of license files to include in the wheel. Supports glob patterns.
    """


@dataclasses.dataclass
class BackportSettings:
    find_python: str = "3.26.1"
    """
    If CMake is less than this value, backport a copy of FindPython. Set
    to 0 disable this, or the empty string.
    """


@dataclasses.dataclass
class EditableSettings:
    mode: str = "redirect"
    """
    Select the editable mode to use. Currently only "redirect" is supported.
    """

    verbose: bool = True
    """
    Turn on verbose output for the editable mode rebuilds.
    """

    rebuild: bool = False
    """
    Rebuild the project when the package is imported.
    The build-directory must be set.
    """


@dataclasses.dataclass
class InstallSettings:
    components: List[str] = dataclasses.field(default_factory=list)
    """
    The components to install. If empty, the default is used.
    """

    strip: Optional[bool] = None
    """
    Whether to strip the binaries. True for scikit-build-core 0.5+.
    """


@dataclasses.dataclass
class ScikitBuildSettings:
    cmake: CMakeSettings = dataclasses.field(default_factory=CMakeSettings)
    ninja: NinjaSettings = dataclasses.field(default_factory=NinjaSettings)
    logging: LoggingSettings = dataclasses.field(default_factory=LoggingSettings)
    sdist: SDistSettings = dataclasses.field(default_factory=SDistSettings)
    wheel: WheelSettings = dataclasses.field(default_factory=WheelSettings)
    backport: BackportSettings = dataclasses.field(default_factory=BackportSettings)
    metadata: Dict[str, Dict[str, Any]] = dataclasses.field(default_factory=dict)
    editable: EditableSettings = dataclasses.field(default_factory=EditableSettings)
    install: InstallSettings = dataclasses.field(default_factory=InstallSettings)

    strict_config: bool = True
    """
    Strictly check all config options. If False, warnings will be
    printed for unknown options. If True, an error will be raised.
    """

    experimental: bool = False
    """
    Enable early previews of features not finalized yet.
    """

    minimum_version: Optional[str] = None
    """
    If set, this will provide a method for backward compatibility.
    """

    build_dir: str = ""
    """
    The build directory. Defaults to a temporary directory, but can be set.
    """
