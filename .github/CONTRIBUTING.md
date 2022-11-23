# Setting up for development

See the [Scikit-HEP Developer introduction][skhep-dev-intro] for a detailed
description of best practices for developing packages.

[skhep-dev-intro]: https://scikit-hep.org/developer/intro

## Quick development

The fastest way to start with development is to use nox. If you don't have nox,
you can use `pipx run nox` to run it without installing, or `pipx install nox`.
If you don't have pipx (pip for applications), then you can install with with
`pip install pipx` (the only case were installing an application with regular
pip is reasonable). If you use macOS, then pipx and nox are both in brew, use
`brew install pipx nox`.

To use, run `nox`. This will lint and test using every installed version of
Python on your system, skipping ones that are not installed. You can also run
specific jobs:

```console
$ nox -s lint  # Lint only
$ nox -s tests-3.9  # Python 3.9 tests only
$ nox -s docs -- serve  # Build and serve the docs
$ nox -s build  # Make an SDist and wheel
```

Nox handles everything for you, including setting up an temporary virtual
environment for each run.

## Setting up a development environment manually

You can set up a development environment by running:

```bash
python3 -m venv .venv
source ./.venv/bin/activate
pip install -v -e .[dev]
```

If you have the
[Python Launcher for Unix](https://github.com/brettcannon/python-launcher), you
can instead do:

```bash
py -m venv .venv
py -m install -v -e .[dev]
```

## Post setup

You should prepare pre-commit, which will help you by checking that commits pass
required checks:

```bash
pip install pre-commit # or brew install pre-commit on macOS
pre-commit install # Will install a pre-commit hook into the git repo
```

You can also/alternatively run `pre-commit run` (changes only) or
`pre-commit run --all-files` to check even without installing the hook.

## Testing

Use pytest to run the unit checks:

```bash
pytest
```

## Quick local running

You can use this to build and use this with an isolated environment:

```bash
pipx run build --wheel
PIP_FIND_LINKS="dist" pipx run build --wheel tests/packages/simple_pyproject_ext -o dist
```

## Building docs

You can build the docs using:

```bash
nox -s docs
```

You can see a preview with:

```bash
nox -s docs -- serve
```

## Pre-commit

This project uses pre-commit for all style checking. While you can run it with
nox, this is such an important tool that it deserves to be installed on its own.
Install pre-commit and run:

```bash
pre-commit run -a
```

to check all files.

# Design info

This section covers the design of scikit-build-core.

Included modules:

- `.cmake`: `CMake`/`CMaker` general interface for building code
- `.fileapi`: Interface for reading the CMake File API
- `.builder`: Generalized backend builder and related helpers
- `.build`: PEP 517 builder
- `.setuptools`: The setuptools Extension interface (and PEP 517 hooks)
- `.setuptools.build_api`: Wrapper injecting build requirements
- `.settings`: The configuration system, reading from pyproject.toml, PEP 517
  config, and envvars

## Basic CMake usage

```python
cmake = CMake.default_search(minimum_version="3.15")
config = CMaker(
    cmake,
    source_dir=source_dir,
    build_dir=build_dir,
    build_type="Release",
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
from scikit_build_core.settings.skbuild_settings import SettingsReader

settings_reader = SettingsReader(Path("pyproject.toml"), config_settings or {})
setting = settings_reader.settings
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
cmake_minimum_required(VERSION 3.15...3.25)
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

setup(
    name="cmake_example",
    version="0.0.1",
    cmake_source_dir=".",
    zip_safe=False,
    extras_require={"test": ["pytest>=6.0"]},
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
cmake_minimum_required(VERSION 3.15...3.25)
project("${SKBUILD_PROJECT_NAME}" LANGUAGES CXX VERSION "${SKBUILD_PROJECT_VERSION}")

find_package(pybind11 CONFIG REQUIRED)
pybind11_add_module(cmake_example src/main.cpp)

target_compile_definitions(cmake_example
                           PRIVATE VERSION_INFO=${PROJECT_VERSION})

install(TARGETS cmake_example DESTINATION .)
```

This is built on top of CMakeExtension, which looks like this:

```
from scikit_build_core.setuptoools.extension import CMakeExtension
...
cmake_extensions=[CMakeExtension("cmake_example")],
```

Which should eventually support multiple extensions.
