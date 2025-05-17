# scikit-build-core

[![Documentation Status][rtd-badge]][rtd-link]
[![GitHub Discussion][github-discussions-badge]][github-discussions-link]
[![Discord][discord-badge]][discord-link]

[![Actions Status][actions-badge]][actions-link]
[![codecov][codecov-badge]][codecov-link]

[![PyPI version][pypi-version]][pypi-link]
[![Conda-Forge][conda-badge]][conda-link]
[![PyPI platforms][pypi-platforms]][pypi-link]
[![Downloads][download-badge]][download-link]

> [!NOTE]
>
> We have a public Scikit-build community meeting every month!
> [Join us on Google Meet](https://meet.google.com/hzu-znrd-uef) on the third
> Friday of every month at 12:00 PM EST. We also have a developer's meeting on
> the first Friday of every month at the same time. Our past meeting minutes are
> [available here](https://github.com/orgs/scikit-build/discussions/categories/community-meeting-notes).

<!-- SPHINX-START -->

Scikit-build-core is a build backend for Python that uses CMake to build
extension modules. It has a simple yet powerful static configuration system in
pyproject.toml, and supports almost unlimited flexibility via CMake. It was
initially developed to support the demanding needs of scientific users, but can
build any sort of package that uses CMake.

Scikit-build-core is a ground-up rewrite of the classic Scikit-build. The key
features of scikit-build classic (which is setuptools based) are also present
here:

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
- SDists are reproducible by default (UNIX, Python 3.9+, uncompressed comparison
  recommended)
- Support for caching between builds (opt-in by setting `build-dir`)
- Support for writing out to extra wheel folders (scripts, headers, data)
- Support for selecting install components and build targets
- Dedicated entrypoints for module and prefix directories
- Several integrated dynamic metadata plugins (proposing standardized support
  soon)
- Experimental editable mode support, with optional experimental auto rebuilds
  on import and optional in-place mode
- Supports WebAssembly (Emscripten/[Pyodide](https://pyodide.org)).
- Supports [free-threaded Python 3.13](https://py-free-threading.github.io).

The following limitations are present compared to classic scikit-build:

- The minimum supported CMake is 3.15
- The minimum supported Python is 3.8 (3.7+ for 0.10.x and older)

Some known missing features that will be developed soon:

- Wheels are not fully reproducible yet (nor are they in most others systems,
  including setuptools)
- Several editable mode caveats (mentioned in the docs).

Other backends are also planned:

- Setuptools integration highly experimental
- Hatchling plugin highly experimental

The recommended interface is the native pyproject builder. There is also a WIP
setuptools-based interface that is being developed to provide a transition path
for classic scikit-build, and a WIP Hatchling plugin. Both might be moved to
standalone packages in the future.

> [!WARNING]
>
> Only the pyproject-based builder should be used; the setuptools backend is
> experimental and likely to move to a separate package before being declared
> stable, and internal API is still being solidified. A future version of this
> package will support creating new build extensions.

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
the minimum to get started.

An example `CMakeLists.txt`:

```cmake
cmake_minimum_required(VERSION 3.15...3.30)
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
`-C` options, or `SKBUILD_*` for environment variables.

For a full reference and explanation of the variables see the [online
documentation][conf-ref]

A quick summary and some defaults are listed below:

<!-- [[[cog
from scikit_build_core.settings.skbuild_docs_readme import mk_skbuild_docs

print("\n```toml\n[tool.scikit-build]")
print(mk_skbuild_docs())
print("```\n")
]]] -->

```toml
[tool.scikit-build]
# The versions of CMake to allow as a python-compatible specifier.
cmake.version = ""

# A list of args to pass to CMake when configuring the project.
cmake.args = []

# A table of defines to pass to CMake when configuring the project. Additive.
cmake.define = {}

# The build type to use when building the project.
cmake.build-type = "Release"

# The source directory to use when building the project.
cmake.source-dir = "."

# The versions of Ninja to allow.
ninja.version = ">=1.5"

# Use Make as a fallback if a suitable Ninja executable is not found.
ninja.make-fallback = true

# The logging level to display.
logging.level = "WARNING"

# Files to include in the SDist even if they are skipped by default. Supports gitignore syntax.
sdist.include = []

# Files to exclude from the SDist even if they are included by default. Supports gitignore syntax.
sdist.exclude = []

# Try to build a reproducible distribution.
sdist.reproducible = true

# If set to True, CMake will be run before building the SDist.
sdist.cmake = false

# A list of packages to auto-copy into the wheel.
wheel.packages = ["src/<package>", "python/<package>", "<package>"]

# The Python version tag used in the wheel file.
wheel.py-api = ""

# Fill out extra tags that are not required.
wheel.expand-macos-universal-tags = false

# The CMake install prefix relative to the platlib wheel path.
wheel.install-dir = ""

# A list of license files to include in the wheel. Supports glob patterns.
wheel.license-files = ""

# Run CMake as part of building the wheel.
wheel.cmake = true

# Target the platlib or the purelib.
wheel.platlib = ""

# A set of patterns to exclude from the wheel.
wheel.exclude = []

# The build tag to use for the wheel. If empty, no build tag is used.
wheel.build-tag = ""

# If CMake is less than this value, backport a copy of FindPython.
backport.find-python = "3.26.1"

# Select the editable mode to use. Can be "redirect" (default) or "inplace".
editable.mode = "redirect"

# Turn on verbose output for the editable mode rebuilds.
editable.verbose = true

# Rebuild the project when the package is imported.
editable.rebuild = false

# Extra args to pass directly to the builder in the build step.
build.tool-args = []

# The build targets to use when building the project.
build.targets = []

# Verbose printout when building.
build.verbose = false

# Additional ``build-system.requires``.
build.requires = []

# The components to install.
install.components = []

# Whether to strip the binaries.
install.strip = true

# The path (relative to platlib) for the file to generate.
generate[].path = ""

# The template string to use for the file.
generate[].template = ""

# The path to the template file. If empty, a template must be set.
generate[].template-path = ""

# The place to put the generated file.
generate[].location = "install"

# A message to print after a build failure.
messages.after-failure = ""

# A message to print after a successful build.
messages.after-success = ""

# Add the python build environment site_packages folder to the CMake prefix paths.
search.site-packages = true

# List dynamic metadata fields and hook locations in this table.
metadata = {}

# Strictly check all config options.
strict-config = true

# Enable early previews of features not finalized yet.
experimental = false

# If set, this will provide a method for backward compatibility.
minimum-version = "0.11"  # current version

# The CMake build directory. Defaults to a unique temporary directory.
build-dir = ""

# Immediately fail the build. This is only useful in overrides.
fail = false

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
- [cmeel][]: A different attempt at a standards compliant builder for CMake.
  Focus on building an ecosystem around a special unimportable folder in
  site-packages (similar to scikit-build's usage of `cmake.*` entrypoints, but
  folder-based).
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

Support for this work was provided by NSF grant [OAC-2209877][]. Any opinions,
findings, and conclusions or recommendations expressed in this material are
those of the author(s) and do not necessarily reflect the views of the National
Science Foundation.

<!-- prettier-ignore-start -->
[OAC-2209877]:              https://www.nsf.gov/awardsearch/showAward?AWD_ID=2209877&HistoricalAwards=false
[actions-badge]:            https://github.com/scikit-build/scikit-build-core/workflows/CI/badge.svg
[actions-link]:             https://github.com/scikit-build/scikit-build-core/actions
[cmeel]:                    https://github.com/cmake-wheel/cmeel
[codecov-badge]:            https://codecov.io/gh/scikit-build/scikit-build-core/branch/main/graph/badge.svg?token=ZLbQzIvyG8
[codecov-link]:             https://codecov.io/gh/scikit-build/scikit-build-core
[conda-badge]:              https://img.shields.io/conda/vn/conda-forge/scikit-build-core
[conda-link]:               https://github.com/conda-forge/scikit-build-core-feedstock
[conf-ref]:                 https://scikit-build-core.readthedocs.io/en/latest/reference/configs.html
[discord-badge]:            https://img.shields.io/discord/803025117553754132?label=Discord%20chat%20%23scikit-build
[discord-link]:             https://discord.gg/pypa
[download-badge]:           https://static.pepy.tech/badge/scikit-build-core/month
[download-link]:            https://pepy.tech/project/scikit-build-core
[enscons]:                  https://pypi.org/project/enscons
[github-discussions-badge]: https://img.shields.io/static/v1?label=Discussions&message=Ask&color=blue&logo=github
[github-discussions-link]:  https://github.com/orgs/scikit-build/discussions
[hatchling]:                https://hatch.pypa.io/latest
[maturin]:                  https://www.maturin.rs
[meson-python]:             https://mesonbuild.com/meson-python
[py-build-cmake]:           https://tttapa.github.io/py-build-cmake
[pypi-link]:                https://pypi.org/project/scikit-build-core/
[pypi-platforms]:           https://img.shields.io/pypi/pyversions/scikit-build-core
[pypi-version]:             https://badge.fury.io/py/scikit-build-core.svg
[rtd-badge]:                https://readthedocs.org/projects/scikit-build-core/badge/?version=latest
[rtd-link]:                 https://scikit-build-core.readthedocs.io/en/latest/?badge=latest
<!-- prettier-ignore-end -->
