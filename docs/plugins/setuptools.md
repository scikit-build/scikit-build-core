# Setuptools

A setuptools plugin is being developed for scikit-build-core, primarily to
enable scikit-build-core to be the build backend for scikit-build (classic).

:::{warning}

This plugin is experimental, and will probably be moved to a separate package.
If using it, it is probably best to upper-cap scikit-build-core until it moves.

:::

## Basic usage

To use the plugin, make sure you have both setuptools and scikit-build-core in
your `build-system.requires` table. You can use either `setuptools.build_meta`
or `scikit-build-core.setuptools.build_meta` as `build-system.build-backend`,
but the latter will give you the auto-inclusion of `cmake` and `ninja` as
needed, so it is recommended.

```toml
[build-system]
requires = ["scikit-build-core", "setuptools"]
build-backend = "scikit_build_core.setuptools.build_meta"
```

Depending on how you like configuring setuptools, you can specify a `project`
table, or use `setup.cfg`, or `setup.py`. However, you need at least this
minimal `setup.py` present:

```python
from setuptools import setup

setup(cmake_source_dir=".")
```

The presence of the `cmake_source_dir` option will tell the scikit-build
setuptools plugin that it can activate for this package.

## Options

These are the currently supported `setup.py` options:

- `cmake_source_dir`: The location of your `CMakeLists.txt`. Required.
- `cmake_args`: Arguments to include when configuring.

These options from scikit-build (classic) are not currently supported:
`cmake_install_dir`, `cmake_with_sdist`, `cmake_process_manifest_hook`, and
`cmake_install_target`. `cmake_languages` has no effect. And
`cmake_minimum_requires_version` is now specified via `pyproject.toml` config,
so has no effect here.

A compatibility shim, `scikit_build_core.setuptools.wrapper.setup` is provided;
it will eventually behave as close to scikit-build (classic)'s `skbuild.setup`
as possible.

## Configuration

All other configuration is available as normal `tool.scikit-build` in
`pyproject.toml` or environment variables as applicable. Config-settings is
_not_ supported, as setuptools has very poor support for config-settings.
Eventually, the build hook might pre-process options, but it's tricky to pass
them through, so it will probably require use cases to be presented.
