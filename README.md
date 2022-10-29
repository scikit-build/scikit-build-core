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

The following limitations are present compared to classic scikit-build:

- The minimum supported CMake is 3.15
- The minimum supported Python is 3.7
- Only the Ninja generator is supported on UNIX
- Only the MSVC generator (currently not tied to the current Python) is
  supported on Windows

Some of these limitations might be adjusted over time, based on user
requirements & effort / maintainability.

This is very much a WIP, some missing features:

- The extensionlib integration is missing
- No hatchling plugin yet
- The docs are not written
- The logging system doesn't work very well
- Dedicated entrypoints still need to be designed
- No support for other targets besides install
- C++17 is required for the test suite because it's more fun than C++11/14
- No support for caching between builds
- No editable mode support
- No extra directories (like headers) supported yet

Included modules:

- `.cmake` `CMake`/`CMakeConfig`: general interface for building code
- `.fileapi`: Interface for reading the CMake File API
- `.builder`: Generalized backend builder and related helpers
- `.pyproject`: PEP 517 builder (used by the PEP 517 interface)
- `.build`: The PEP 517 interface
- `.setuptools`: The setuptools Extension interface (and PEP 517 hooks)
- `.setuptools.build_api`: Wrapper injecting build requirements
- `.settings`: The configuration system, reading from pyproject.toml, PEP 517
  config, and envvars

Features over classic Scikit-build:

- Better warnings and errors
- No warning about unused variables
- Automatically adds Ninja and/or CMake only as required
- Closer to vanilla setuptools in setuptools mode, doesn't interfere with config
- Powerful config system
- Automatic inclusion of site-packages in CMAKE_PREFIX_PATH
- FindPython is backported if running on CMake < 3.24 (included via hatchling in
  a submodule)

## Basic CMake usage

```python
cmake = CMake.default_search(minimum_version="3.15")
config = CMakeConfig(
    cmake,
    source_dir=source_dir,
    build_dir=build_dir,
)
config.configure()
config.build()
config.install(prefix)
```

## File API

If you want to access the File API, use:

```python
from scikit_build_core.fileapi.query import stateless_query
from scikit_build_core.fileapi.reply import load_reply_dir

reply_dir = stateless_query(config.build_dir)
config.configure()
index = load_reply_dir(reply_dir)
```

This mostly wraps the FileAPI in classes. It autoloads some jsonFiles. This
throws an `ExceptionGroup` if parsing files. It is currently experimental.

## Configuration

Configuration support uses plain dataclasses:

```python
@dataclasses.dataclass
class NestedSettings:
    one: str


@dataclasses.dataclass
class SettingChecker:
    nested: NestedSettings
```

You can use different sources, currently environment variables:

```yaml
PREFIX_NESTED_ONE: "envvar"
```

PEP 517 config dictionaries:

```python
{"nested.one": "PEP 517 config"}
```

And TOML:

```toml
[tool.cmake]
nested.one = "TOML config"
```

The CMake config is pre-configured and available in `.settings.cmake_model`,
usable as:

```python
from scikit_build_core.settings.skbuild_settings import read_settings

settings = read_skbuild_settings(Path("pyproject.toml"), config_settings or {})
assert settings.cmake.minimum_version == "3.15"
assert settings.ninja.minimum_version == "1.5"
```

## Builders

The tools in `builder` are designed to make writing a builder easy. The
`Builder` class is used in the various builder implementations.

### PEP 517 builder

This is highly experimental, and currently only uses `.gitignore` to filter the
SDist, and the wheel only contains the install directory - control using CMake.

```toml
[build-system]
requires = [
    "scikit_build_core",
    "pybind11",
]
build-backend = "scikit_build_core.build"

[project]
name = "cmake_example"
version = "0.0.1"
requires-python = ">=3.7"

[project.optional-dependencies]
test = ["pytest>=6.0"]
```

```cmake
cmake_minimum_required(VERSION 3.15...3.24)
project("${SKBUILD_PROJECT_NAME}" LANGUAGES CXX VERSION "${SKBUILD_PROJECT_VERSION}")

find_package(pybind11 CONFIG REQUIRED)
pybind11_add_module(cmake_example src/main.cpp)

target_compile_definitions(cmake_example
                           PRIVATE VERSION_INFO=${PROJECT_VERSION})

install(TARGETS cmake_example DESTINATION .)
```

### Setuptools builder

Experimental. Supports only a single module, may not support extra Python files.

`setup.py`:

```python
from setuptools import setup

from scikit_build_core.setuptools.extension import CMakeBuild, CMakeExtension

setup(
    name="cmake_example",
    version="0.0.1",
    ext_modules=[CMakeExtension("cmake_example")],
    zip_safe=False,
    extras_require={"test": ["pytest>=6.0"]},
    cmdclass={"build_ext": CMakeBuild},
    python_requires=">=3.7",
)
```

`pyproject.toml`:

```toml
[build-system]
requires = [
    "scikit_build_core",
    "pybind11",
]
build-backend = "scikit_build_core.setuptools.build_meta"
```

```cmake
cmake_minimum_required(VERSION 3.15...3.24)
project("${SKBUILD_PROJECT_NAME}" LANGUAGES CXX VERSION "${SKBUILD_PROJECT_VERSION}")

find_package(pybind11 CONFIG REQUIRED)
pybind11_add_module(cmake_example src/main.cpp)

target_compile_definitions(cmake_example
                           PRIVATE VERSION_INFO=${PROJECT_VERSION})

install(TARGETS cmake_example DESTINATION .)
```

## Acknowledgements

Support for this work was provided by NSF cooperative agreement [OAC-2209877][].

<!-- prettier-ignore-start -->
[actions-badge]:            https://github.com/henryiii/scikit-build-core/workflows/CI/badge.svg
[actions-link]:             https://github.com/henryiii/scikit-build-core/actions
[black-badge]:              https://img.shields.io/badge/code%20style-black-000000.svg
[black-link]:               https://github.com/psf/black
[conda-badge]:              https://img.shields.io/conda/vn/conda-forge/scikit-build-core
[conda-link]:               https://github.com/conda-forge/scikit-build-core-feedstock
[github-discussions-badge]: https://img.shields.io/static/v1?label=Discussions&message=Ask&color=blue&logo=github
[github-discussions-link]:  https://github.com/scikit-build/scikit-build-core/discussions
[gitter-badge]:             https://badges.gitter.im/https://github.com/scikit-build/scikit-build-core/community.svg
[gitter-link]:              https://gitter.im/https://github.com/scikit-build/scikit-build-core/community?utm_source=badge&utm_medium=badge&utm_campaign=pr-badge
[codecov-badge]: https://codecov.io/gh/henryiii/scikit-build-core/branch/main/graph/badge.svg?token=ZLbQzIvyG8
[codecov-link]: https://codecov.io/gh/henryiii/scikit-build-core
[pypi-link]:                https://pypi.org/project/scikit-build-core/
[pypi-platforms]:           https://img.shields.io/pypi/pyversions/scikit-build-core
[pypi-version]:             https://badge.fury.io/py/scikit-build-core.svg
[rtd-badge]:                https://readthedocs.org/projects/scikit-build-core/badge/?version=latest
[rtd-link]:                 https://scikit-build-core.readthedocs.io/en/latest/?badge=latest
[sk-badge]:                 https://scikit-hep.org/assets/images/Scikit--HEP-Project-blue.svg
[OAC-2209877]:              https://www.nsf.gov/awardsearch/showAward?AWD_ID=2209877&HistoricalAwards=false
<!-- prettier-ignore-end -->
