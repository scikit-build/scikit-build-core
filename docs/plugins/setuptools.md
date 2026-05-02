# Setuptools

A setuptools plugin is being developed for scikit-build-core, primarily to
enable scikit-build-core to be the build backend for scikit-build (classic).

:::{warning}

Use the `[setuptools]` extra when using this plugin. It will ensure a proper
version of setuptools, and will help protect you if the plugin moves to a
separate package in the future. Use this even if you set a higher minimum
version of setuptools (recommended!).

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
- `cmake_install_dir`: Supported. In direct setuptools-plugin usage, this is
  interpreted relative to setuptools' `build_lib` staging directory. When using
  `scikit_build_core.setuptools.wrapper.setup`, the value follows classic
  scikit-build compatibility semantics instead, so source-root-prefixed values
  like `src` continue to work there.

These options from scikit-build (classic) are not currently supported:
`cmake_with_sdist`, `cmake_process_manifest_hook`, and `cmake_install_target`.
`cmake_languages` has no effect. And `cmake_minimum_required_version` is now
specified via `pyproject.toml` config, so has no effect here.

A compatibility shim, `scikit_build_core.setuptools.wrapper.setup` is provided;
it will eventually behave as close to scikit-build (classic)'s `skbuild.setup`
as possible.

## Configuration

All other configuration is available as normal `tool.scikit-build` in
`pyproject.toml` or environment variables as applicable. Config-settings is
_not_ supported, as setuptools has very poor support for config-settings.
Eventually, the build hook might pre-process options, but it's tricky to pass
them through, so it will probably require use cases to be presented.

## Editable installs

PEP 660 editable installs (`pip install -e .`) are supported when the active
setuptools version provides `build_editable` (setuptools 63+).

Setuptools editable installs require:

```toml
[tool.scikit-build]
editable.mode = "inplace"
```

The setuptools plugin follows setuptools' editable-wheel mechanism, so editable
builds place CMake-installed extension modules into the source layout that
setuptools exposes via its `.pth` file. This is effectively the setuptools
equivalent of scikit-build-core's `inplace` editable mode, so redirect mode is
not supported here.

Because of that, `editable.rebuild` is not supported in setuptools mode.
