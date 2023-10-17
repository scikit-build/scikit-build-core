# scikit-build-core

[![Documentation Status][rtd-badge]][rtd-link]
[![GitHub Discussion][github-discussions-badge]][github-discussions-link]
[![Discord][discord-badge]][discord-link]

[![Actions Status][actions-badge]][actions-link]
[![codecov][codecov-badge]][codecov-link]

[![PyPI version][pypi-version]][pypi-link]
[![Conda-Forge][conda-badge]][conda-link]
[![PyPI platforms][pypi-platforms]][pypi-link]

<!-- SPHINX-START -->

Scikit-build-core is a ground-up rewrite of the classic Scikit-build, a bridge
between Python package build systems and CMake, the most popular compiled
language build system. The key features of scikit-build classic (which is
setuptools based) are also present here:

- Great support for or by most OSs, compilers, IDEs, and libraries
- Support for C++ features and other languages like Fortran
- Support for multithreaded builds
- Simple CMakeFiles.txt instead of up to thousands of lines of fragile
  setuptools/distutils code
- Cross-compile support for Apple Silicon and Windows ARM

Scikit-build-core was built using Python packaging standards developed after
scikit-build (classic) was written. Using it directly provides the following
features over classic Scikit-build:

- Better warnings, errors, and logging
- No warning about unused variables
- Automatically adds Ninja and/or CMake only as required
- No dependency on setuptools, distutils, or wheel
- Powerful config system, including config options support
- Automatic inclusion of site-packages in `CMAKE_PREFIX_PATH`
- FindPython is backported if running on CMake < 3.26.1 (configurable), supports
  PyPY SOABI & Limited API / Stable ABI
- Limited API / Stable ABI and pythonless tags supported via config option
- No slow generator search, ninja/make or MSVC used by default, respects
  `CMAKE_GENERATOR`
- SDists are reproducible by default (UNIX, Python 3.9+)
- Support for caching between builds (opt-in by setting `build-dir`)
- Support for writing out to extra wheel folders (scripts, headers, data)
- Support for selecting install components and build targets
- Dedicated entrypoints for module and prefix directories
- Several integrated dynamic metadata plugins (proposing standardized support
  soon)
- Experimental editable mode support, with optional experimental auto rebuilds
  on import
- Supports WebAssembly (Emscripten/Pyodide).

The following limitations are present compared to classic scikit-build:

- The minimum supported CMake is 3.15
- The minimum supported Python is 3.7

Some known missing features that will be developed soon:

- Wheels are not fully reproducible yet (nor are they in most others systems,
  including setuptools)
- Several editable mode caveats (mentioned in the docs).

Other backends are also planned:

- Setuptools integration highly experimental
- The extensionlib integration is missing
- No hatchling plugin yet.

The recommended interface is the native pyproject builder. There is also a WIP
setuptools-based interface that is being developed to provide a transition path
for classic scikit-build.

**WARNING**: Only the pyproject-based builder should be used; the setuptools
backend is experimental and likely to move to a separate package before being
declared stable, and internal API is still being solidified. A future version of
this package will support creating new build extensions.

## Example

To use scikit-build-core, add it to your `build-system.requires`, and specify
the `scikit_build_core.build` builder as your `build-system.build-backend`. You
do _not_ need to specify `cmake` or `ninja`; scikit-build-core will require them
automatically if the system versions are not sufficient.

```toml
[build-system]
requires = ["scikit-build-core"]
build-backend = "scikit_build_core.build"

[project]
name = "scikit_build_simplest"
version = "0.0.1"
```

You can (and should) specify the rest of the entries in `project`, but these are
the minimum to get started. You can also `scikit-build-core[pyproject]` to
pre-load some dependencies if you want; in some cases this might be marginally
faster.

An example `CMakeLists.txt`:

```cmake
cmake_minimum_required(VERSION 3.15...3.27)
project(${SKBUILD_PROJECT_NAME} LANGUAGES C)

find_package(Python COMPONENTS Interpreter Development.Module REQUIRED)

Python_add_library(_module MODULE src/module.c WITH_SOABI)
install(TARGETS _module DESTINATION ${SKBUILD_PROJECT_NAME})
```

Scikit-build-core will backport FindPython from CMake 3.26.1 to older versions
of Python, and will handle PyPy for you if you are building from PyPy. You will
need to install everything you want into the full final path inside site-modules
(so you will usually prefix everything by the package name).

More examples are in the
[tests/packages](https://github.com/scikit-build/scikit-build-core/tree/main/tests/packages).

## Configuration

All configuration options can be placed in `pyproject.toml`, passed via
`-C`/`--config-setting` in build or `-C`/`--config-settings` in `pip` , or set
as environment variables. `tool.scikit-build` is used in toml, `skbuild.` for
`-C` options, or `SKBUILD_*` for environment variables. The defaults are listed
below:

<!-- [[[cog
from scikit_build_core.settings.skbuild_docs import mk_skbuild_docs

print("\n```toml\n[tool.scikit-build]")
print(mk_skbuild_docs())
print("```\n")
]]] -->

```toml
[tool.scikit-build]
# The minimum version of CMake to use. If CMake is not present on the system or
# is older than this, it will be downloaded via PyPI if possible. An empty
# string will disable this check.
cmake.minimum-version = "3.15"

# A list of args to pass to CMake when configuring the project. Setting this in
# config or envvar will override toml. See also ``cmake.define``.
cmake.args = []

# A table of defines to pass to CMake when configuring the project. Additive.
cmake.define = {}

# Verbose printout when building.
cmake.verbose = false

# The build type to use when building the project. Valid options are: "Debug",
# "Release", "RelWithDebInfo", "MinSizeRel", "", etc.
cmake.build-type = "Release"

# The source directory to use when building the project. Currently only affects
# the native builder (not the setuptools plugin).
cmake.source-dir = "."

# The build targets to use when building the project. Empty builds the default
# target.
cmake.targets = []

# The minimum version of Ninja to use. If Ninja is not present on the system or
# is older than this, it will be downloaded via PyPI if possible. An empty
# string will disable this check.
ninja.minimum-version = "1.5"

# If CMake is not present on the system or is older required, it will be
# downloaded via PyPI if possible. An empty string will disable this check.
ninja.make-fallback = true

# The logging level to display, "DEBUG", "INFO", "WARNING", and "ERROR" are
# possible options.
logging.level = "WARNING"

# Files to include in the SDist even if they are skipped by default. Supports
# gitignore syntax.
sdist.include = []

# Files to exclude from the SDist even if they are included by default. Supports
# gitignore syntax.
sdist.exclude = []

# If set to True, try to build a reproducible distribution (Unix and Python 3.9+
# recommended).  ``SOURCE_DATE_EPOCH`` will be used for timestamps, or a fixed
# value if not set.
sdist.reproducible = true

# If set to True, CMake will be run before building the SDist.
sdist.cmake = false

# A list of packages to auto-copy into the wheel. If this is not set, it will
# default to the first of ``src/<package>``, ``python/<package>``, or
# ``<package>`` if they exist.  The prefix(s) will be stripped from the package
# name inside the wheel.
wheel.packages = ["src/<package>", "python/<package>", "<package>"]

# The Python tags. The default (empty string) will use the default Python
# version. You can also set this to "cp37" to enable the CPython 3.7+ Stable ABI
# / Limited API (only on CPython and if the version is sufficient, otherwise
# this has no effect). Or you can set it to "py3" or "py2.py3" to ignore Python
# ABI compatibility. The ABI tag is inferred from this tag.
wheel.py-api = ""

# Fill out extra tags that are not required. This adds "x86_64" and "arm64" to
# the list of platforms when "universal2" is used, which helps older Pip's
# (before 21.0.1) find the correct wheel.
wheel.expand-macos-universal-tags = false

# The install directory for the wheel. This is relative to the platlib root. You
# might set this to the package name. The original dir is still at
# SKBUILD_PLATLIB_DIR (also SKBUILD_DATA_DIR, etc. are available). EXPERIMENTAL:
# An absolute path will be one level higher than the platlib root, giving access
# to "/platlib", "/data", "/headers", and "/scripts".
wheel.install-dir = ""

# A list of license files to include in the wheel. Supports glob patterns.
wheel.license-files = ["LICEN[CS]E*", "COPYING*", "NOTICE*", "AUTHORS*"]

# If CMake is less than this value, backport a copy of FindPython. Set to 0
# disable this, or the empty string.
backport.find-python = "3.26.1"

# Select the editable mode to use. Currently only "redirect" is supported.
editable.mode = "redirect"

# Turn on verbose output for the editable mode rebuilds.
editable.verbose = true

# Rebuild the project when the package is imported. The build-directory must be
# set.
editable.rebuild = false

# The components to install. If empty, all default components are installed.
install.components = []

# Whether to strip the binaries. True for scikit-build-core 0.5+.
install.strip = false

# The path (relative to platlib) for the file to generate.
generate[].path = ""

# The template to use for the file. This includes string.Template style
# placeholders for all the metadata. If empty, a template-path must be set.
generate[].template = ""

# The path to the template file. If empty, a template must be set.
generate[].template-path = ""

# The place to put the generated file. The "build" directory is useful for CMake
# files, and the "install" directory is useful for Python files, usually. You
# can also write directly to the "source" directory, will overwrite existing
# files & remember to gitignore the file.
generate[].location = "install"

# List dynamic metadata fields and hook locations in this table.
metadata = {}

# Strictly check all config options. If False, warnings will be printed for
# unknown options. If True, an error will be raised.
strict-config = true

# Enable early previews of features not finalized yet.
experimental = false

# If set, this will provide a method for backward compatibility.
minimum-version = "0.5"  # current version

# The build directory. Defaults to a temporary directory, but can be set.
build-dir = ""

```

<!-- [[[end]]] -->

Most CMake environment variables should be supported, and `CMAKE_ARGS` can be
used to set extra CMake args. `ARCHFLAGS` is used to specify macOS universal2 or
cross-compiles, just like setuptools.

You can also specify `[[tool.scikit-build.overrides]]` to customize values for
different systems. See the docs for details.

## Other projects for building

Scikit-build-core is a binary build backend. There are also other binary build
backends:

- [py-build-cmake][]: A different attempt at a standards compliant builder for
  CMake. Strong focus on cross-compilation. Uses Flit internals.
- [meson-python][]: A meson-based build backend; has some maintainer overlap
  with scikit-build-core.
- [maturin][]: A build backend for Rust projects, using Cargo.
- [enscons][]: A SCons based backend, not very actively developed (but it
  predates all the others in modern standard support!)

If you don't need a binary build, you don't need to use a binary build backend!
There are some very good Python build backends; we recommend [hatchling][] as a
good balance between good defaults for beginners and good support for advanced
use cases. This is the tool scikit-build-core itself uses.

## Acknowledgements

Support for this work was provided by NSF cooperative agreement [OAC-2209877][].

<!-- prettier-ignore-start -->
[actions-badge]:            https://github.com/scikit-build/scikit-build-core/workflows/CI/badge.svg
[actions-link]:             https://github.com/scikit-build/scikit-build-core/actions
[black-badge]:              https://img.shields.io/badge/code%20style-black-000000.svg
[black-link]:               https://github.com/psf/black
[conda-badge]:              https://img.shields.io/conda/vn/conda-forge/scikit-build-core
[conda-link]:               https://github.com/conda-forge/scikit-build-core-feedstock
[github-discussions-badge]: https://img.shields.io/static/v1?label=Discussions&message=Ask&color=blue&logo=github
[github-discussions-link]:  https://github.com/orgs/scikit-build/discussions
[discord-badge]:            https://img.shields.io/discord/803025117553754132?label=Discord%20chat%20%23scikit-build
[discord-link]:             https://discord.gg/pypa
[codecov-badge]:            https://codecov.io/gh/scikit-build/scikit-build-core/branch/main/graph/badge.svg?token=ZLbQzIvyG8
[codecov-link]:             https://codecov.io/gh/scikit-build/scikit-build-core
[pypi-link]:                https://pypi.org/project/scikit-build-core/
[pypi-platforms]:           https://img.shields.io/pypi/pyversions/scikit-build-core
[pypi-version]:             https://badge.fury.io/py/scikit-build-core.svg
[rtd-badge]:                https://readthedocs.org/projects/scikit-build-core/badge/?version=latest
[rtd-link]:                 https://scikit-build-core.readthedocs.io/en/latest/?badge=latest
[OAC-2209877]:              https://www.nsf.gov/awardsearch/showAward?AWD_ID=2209877&HistoricalAwards=false
[hatchling]:                https://hatch.pypa.io/latest
[maturin]:                  https://www.maturin.rs
[meson-python]:             https://meson-python.readthedocs.io
[enscons]:                  https://pypi.org/project/enscons
[py-build-cmake]:           https://tttapa.github.io/py-build-cmake
<!-- prettier-ignore-end -->
