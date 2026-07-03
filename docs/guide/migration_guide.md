# Migrating from scikit-build

## Config changes

- The `build-system.build-backend` key in pyproject.toml must be changed to
  `scikit_build_core.build`.
- Replace `scikit-build` with `scikit-build-core` in `build-system.requires`.
- You should remove `cmake` and `ninja` from `build-system.requires`;
  scikit-build-core adds them only when necessary (see
  [getting started](#python-package-configuration)). Instead, set minimum
  required versions with `cmake.version` and `ninja.version` in the
  `[tool.scikit-build]` table.
- You must fill out the `tool.scikit-build` table in pyproject.toml, see
  [getting started](getting_started.md) for more information.
- If your project is primarily configured using setup.py or setup.cfg, you will
  need to move the configuration to pyproject.toml. The
  [project metadata spec](https://packaging.python.org/en/latest/specifications/pyproject-toml)
  shows the information that can be placed directly in the project table. For
  additional metadata, see [our configuration guide](../configuration/index.md).
- If you specify files to include in sdists via MANIFEST.in, use the
  `sdist.include` and `sdist.exclude` settings instead (see
  [source file inclusion](../configuration/index.md#configuring-source-file-inclusion)).
  Scikit-build-core uses all non `.gitignore`'d files by default, so this is
  often minimal or not needed.

```{tip}
A useful trick for migrating setup.py/setup.cfg configuration is to change the
`build-backend` from `skbuild` to `setuptools`, install `hatch`, and run
`hatch new --init`. This automatically migrates the configuration to
pyproject.toml, after which you can change the `build-backend` to
`scikit_build_core.build`.
```

## CMake changes

scikit-build users wishing to switch to scikit-build-core should be aware of the
following changes that must be made to their CMake files:

- The PythonExtensions CMake module distributed with scikit-build is not part of
  scikit-build-core. Due to improvements in CMake's built-in support for
  building Python extension modules, most of this module is no longer necessary.
  Change

```cmake
find_package(PythonExtensions REQUIRED)
add_library(${LIBRARY} MODULE ${FILENAME})
python_extension_module(${LIBRARY})
```

to

```cmake
find_package(Python COMPONENTS Interpreter Development.Module REQUIRED)
python_add_library(${LIBRARY} MODULE WITH_SOABI ${FILENAME})
```

- The UseCython CMake module distributed with scikit-build (classic) is replaced
  by the standalone [cython-cmake][] package; see the Cython tab in
  [getting started](#cmake-file) for an example.

[cython-cmake]: https://github.com/scikit-build/cython-cmake

- The `SKBUILD_CONFIGURE_OPTIONS` environment variable is now named
  `SKBUILD_CMAKE_ARGS` for consistency (the
  [setuptools wrapper shim](../plugins/setuptools.md) is the one exception that
  still honors the old name).
- The `SKBUILD_BUILD_OPTIONS` environment variable is not supported. Some
  specific features are accessible using alternative variables. In particular,
  use `CMAKE_BUILD_PARALLEL_LEVEL` or `SKBUILD_BUILD_VERBOSE` to control build
  parallelism or CMake verbosity directly.
