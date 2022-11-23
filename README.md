# scikit-build-core

[![Actions Status][actions-badge]][actions-link]
[![Documentation Status][rtd-badge]][rtd-link]
[![Code style: black][black-badge]][black-link]
[![codecov][codecov-badge]][codecov-link]

<!-- Not implemented yet
[![PyPI version][pypi-version]][pypi-link]
[![Conda-Forge][conda-badge]][conda-link]
[![PyPI platforms][pypi-platforms]][pypi-link]

[![GitHub Discussion][github-discussions-badge]][github-discussions-link]
[![Gitter][gitter-badge]][gitter-link]
-->

**WARNING**: Only the pyproject-based builder should be used (setuptools backend
is experimental and likely to move to a separate package), and internal API is
still being solidified. A future version of this package will support creating
new build extensions.

The following limitations are present compared to classic scikit-build:

- The minimum supported CMake is 3.15
- The minimum supported Python is 3.7

Some known missing features that will be developed soon:

- No support for caching between builds
- No editable mode support
- The docs are not written
- Dedicated entrypoints are planned for projects wanting to support discovery
- No support for other targets besides install
- Wheels are not fully reproducible yet
- Windows ARM support missing

Other backends are also planned:

- Setuptools integration highly experimental currently
- The extensionlib integration is missing
- No hatchling plugin yet

Features over classic Scikit-build:

- Better warnings, errors, and logging
- No warning about unused variables
- Automatically adds Ninja and/or CMake only as required
- No dependency on setuptools, distutils, or wheel in build mode.
- Powerful config system, including config options support in build mode.
- Automatic inclusion of site-packages in `CMAKE_PREFIX_PATH`
- FindPython is backported if running on CMake < 3.24 (included via hatchling in
  a submodule, configurable)
- Limited API / Stable ABI and pythonless tags supported via config option
- No slow generator search, ninja/make or MSVC used by default, respects
  `CMAKE_GENERATOR`
- SDists are reproducible by default (UNIX, Python 3.9+)

Currently, the recommended interface is the PEP 517 interface. There is also a
setuptools-based interface that is being developed to provide a transition path
for classic scikit-build.

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
the minimum to get started. You can also add the `rich` (more colorful
printouts) or `pyproject` (pre-load some dependencies) extras if you want.

An example `CMakeLists.txt`:

```cmake
cmake_minimum_required(VERSION 3.15...3.25)

project(${SKBUILD_PROJECT_NAME} LANGUAGES C VERSION ${SKBUILD_PROJECT_VERSION})

find_package(Python COMPONENTS Interpreter Development.Module)

Python_add_library(_module MODULE src/module.c WITH_SOABI)
set(Python_SOABI ${SKBUILD_SOABI})  # Required for PyPy support

install(TARGETS _module DESTINATION ${SKBUILD_PROJECT_NAME})
```

Scikit-build-core will backport FindPython from CMake 3.24 to older versions of
Python, and will handle PyPy for you if you are building from PyPy. You will
need to install everything you want into the full final path inside site-modules
(so you will usually prefix everything by the package name).

More examples are in the
[tests/packages](https://github.com/scikit-build/scikit-build-core/tree/main/tests/packages).

## Configuration

All configuration options can be placed in `pyproject.toml`, passed via `-C` or
`--config-setting` in build or `--config-settings` in `pip` (warning: pip
doesn't support list options), or set as environment variables.
`tool.scikit-build` is used in toml, `skbuild.` for `-C` options, or `SKBUILD_*`
for environment variables. The defaults are listed below:

```toml
[tool.scikit-build]
# The PEP 517 build hooks will add ninja and/or cmake if the versions on the
# system are not at least these versions. Disabled by an empty string.
cmake.minimum-version = "3.15"
ninja.minimum-version = "1.5"

# Fallback on gmake/make if available and ninja is missing (Unix). Will only
# fallback on platforms without a known ninja wheel.
ninja.make-fallback = true

# Extra args for CMake. Pip, unlike build, does not support lists, so simicolon
# can be used to separate. Setting this in config or envvar will override the
# entire list). See also cmake.define.
cmake.args = []

# This activates verbose builds
cmake.verbose = false

# This controls the CMake build type
cmake.build-type = "Release"

# Display logs at or above this level.
logging.level = "WARNING"

# Include and exclude patterns, in gitignore syntax. Include overrides exclude.
# Wheels include packages included in the sdist; CMake has the final say.
sdist.include = []
sdist.exclude = []

# Make reproducible SDists (Python 3.9+ and UNIX recommended). Respects
# SOURCE_DATE_EPOCH when true (the default).
sdist.reproducible = true

# The root-level packages to include. Special default: if not given, the package
# is auto-discovered if it's name matches the main name.
wheel.packages = ["src/<package>", "<package>"]

# Setting py-api to "cp37" would build ABI3 wheels for Python 3.7+.  If CPython
# is less than this value, or on PyPy, this will be ignored.  Setting the api to
# "py3" or "py2.py3" would build wheels that don't depend on Python (ctypes,
# etc).
wheel.py-api = ""

# Setting this to true will expand tags (universal2 will add Intel and Apple
# Silicon tags, for pip <21.0.1 compatibility).
wheel.expand-macos-universal-tags = false

# This allows you to change the install dir, such as to the package name. The
# original dir is still at SKBUILD_PLATLIB_DIR (also SKBUILD_DATA_DIR, etc. are
# available)
wheel.install-dir = "."

# This will backport an internal copy of FindPython if CMake is less than this
# value. Set to 0 or the empty string to disable. The default will be kept in
# sync with the version of FindPython stored in scikit-build-core.
backport.find-python = "3.24"

# Enable experimental features if any are available
experimental = false

# Strictly validate config options
strict-config = true

# This provides some backward compatibility if set. Defaults to the latest
# scikit-build-core version.
minimum-version = "0.1"  # current version

[tool.scikit-build.cmake.define]
# Put CMake defines in this table.
```

Most CMake environment variables should be supported, and `CMAKE_ARGS` can be
used to set extra CMake args. `ARCHFLAGS` is used to specify macOS universal2 or
cross-compiles, just like setuptools.

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
[github-discussions-link]:  https://github.com/scikit-build/scikit-build-core/discussions
[gitter-badge]:             https://badges.gitter.im/https://github.com/scikit-build/scikit-build-core/community.svg
[gitter-link]:              https://gitter.im/https://github.com/scikit-build/scikit-build-core/community?utm_source=badge&utm_medium=badge&utm_campaign=pr-badge
[codecov-badge]:            https://codecov.io/gh/scikit-build/scikit-build-core/branch/main/graph/badge.svg?token=ZLbQzIvyG8
[codecov-link]:             https://codecov.io/gh/scikit-build/scikit-build-core
[pypi-link]:                https://pypi.org/project/scikit-build-core/
[pypi-platforms]:           https://img.shields.io/pypi/pyversions/scikit-build-core
[pypi-version]:             https://badge.fury.io/py/scikit-build-core.svg
[rtd-badge]:                https://readthedocs.org/projects/scikit-build-core/badge/?version=latest
[rtd-link]:                 https://scikit-build-core.readthedocs.io/en/latest/?badge=latest
[sk-badge]:                 https://scikit-hep.org/assets/images/Scikit--HEP-Project-blue.svg
[OAC-2209877]:              https://www.nsf.gov/awardsearch/showAward?AWD_ID=2209877&HistoricalAwards=false
<!-- prettier-ignore-end -->
