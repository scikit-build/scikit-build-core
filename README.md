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
- Only the MSVC generator (not tied to the current Python) is supported on
  Windows
- Only FindPython is supported

Some of these limitations might be adjusted over time, based on user
requirements & effort / maintainability.

This is very much a WIP, some missing features:

- PEP 517 config
- The extensionlib integration is missing
- The docs are not written
- No PEP 517 interface is currently present
- No discovery system is present
- No support for other targets besides install
- C++17 is required for the test suite because it's more fun than C++11/14

Included features:

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

Works.

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
assert settings.cmake.min_version == "3.15"
assert settings.ninja.min_version == "0.0"
```

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
<!-- prettier-ignore-end -->
