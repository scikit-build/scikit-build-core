# Setuptools

Scikit-build-core includes an experimental setuptools plugin, primarily to
enable scikit-build-core to be the build backend for scikit-build (classic).

:::{warning}

Use the `[setuptools]` extra when using this plugin. It will ensure a proper
version of setuptools, and will help protect you if the plugin moves to a
separate package in the future. Use this even if you set a higher minimum
version of setuptools (recommended!).

:::

:::{versionadded} 1.0

The `[setuptools]` extra.

:::

## Basic usage

To use the plugin, make sure you have both setuptools and scikit-build-core in
your `build-system.requires` table. You can use either `setuptools.build_meta`
or `scikit_build_core.setuptools.build_meta` as `build-system.build-backend`,
but the latter will give you the auto-inclusion of `cmake` and `ninja` as
needed, so it is recommended.

```toml
[build-system]
requires = ["scikit-build-core[setuptools]"]
build-backend = "scikit_build_core.setuptools.build_meta"
```

Depending on how you like configuring setuptools, you can specify a `project`
table, or use `setup.cfg`, or `setup.py`. However, you need at least this
minimal `setup.py` present:

```python
from setuptools import setup

setup(cmake_source_dir=".")
```

or this in your `pyproject.toml`:

```toml
[tool.scikit-build]
cmake.source-dir = "."
```

The presence of the `cmake_source_dir` option or a `cmake.source-dir` setting
will tell the scikit-build setuptools plugin that it can activate for this
package.

## Options

Most options should be set via `[tool.scikit-build]`. These classic `setup.py`
options are also supported, though:

- `cmake_source_dir`: The location of your `CMakeLists.txt`. Required, unless
  set via `cmake.source-dir` in `[tool.scikit-build]`.
- `cmake_args`: Arguments to include when configuring.
- `cmake_install_dir`: Supported. In direct setuptools-plugin usage, this is
  interpreted relative to setuptools' `build_lib` staging directory. When using
  `scikit_build_core.setuptools.wrapper.setup`, the value follows classic
  scikit-build compatibility semantics instead, so source-root-prefixed values
  like `src` continue to work there.
- `cmake_process_manifest_hook`: A callable that receives the list of files
  installed by CMake, relative to the CMake install prefix, and returns the
  subset that should be kept. For editable installs the omitted files are
  removed from the source tree.
- `cmake_install_target`: The build target that performs the install. The
  default, `"install"`, runs `cmake --install`. Any other value installs by
  running `cmake --build --target <value>` (equivalent to setting
  `install.targets`), for projects with an umbrella install target.

```{versionadded} 1.0
Support for the `cmake_install_dir`, `cmake_process_manifest_hook`, and
`cmake_install_target` options.
```

`cmake_with_sdist`, from scikit-build (classic), is not supported (didn't work
correctly). `cmake_languages` has no effect. `cmake_minimum_required_version` is
now specified via `pyproject.toml` config, so has no effect here.

A compatibility shim, `scikit_build_core.setuptools.wrapper.setup` is provided;
it aims to behave as close to scikit-build (classic)'s `skbuild.setup` as
possible. If you don't use that, you get more reasonable modern defaults.

## Configuration

All other configuration is available as normal `tool.scikit-build` in
`pyproject.toml` or environment variables as applicable. Config-settings is
_not_ supported, as setuptools has very poor support for config-settings.

For classic scikit-build compatibility, two environment variables are honored,
but only when using the `scikit_build_core.setuptools.wrapper.setup` shim (they
have no effect in the general setuptools plugin or the main build backend):

- `SKBUILD_CONFIGURE_OPTIONS`: extra arguments appended when configuring (the
  wrapper's analog of the backend's `SKBUILD_CMAKE_ARGS`).
- `SKBUILD_BUILD_OPTIONS`: extra arguments forwarded to `cmake --build`. Use a
  leading `--` to pass native build-tool options, e.g.
  `SKBUILD_BUILD_OPTIONS="-- -l4"`.

Both are split following shell quoting rules, so quoted values with spaces are
preserved.

```{versionadded} 1.0
The `SKBUILD_CONFIGURE_OPTIONS` and `SKBUILD_BUILD_OPTIONS` environment
variables (honored by the `wrapper.setup` shim).
```

## Editable installs

```{versionadded} 1.0

```

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
equivalent of scikit-build-core's
[`inplace` editable mode](../configuration/editable.md#inplace-mode), so
redirect mode is not supported here.

Because of that, `editable.rebuild` is not supported in setuptools mode.

A direct `setup.py build_ext --inplace` builds into the source tree without
producing an editable wheel, so it works without any `editable.mode` setting,
just like scikit-build (classic).
