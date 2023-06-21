# Migrating from scikit-build

```{warning}
scikit-build-core is under active development. This guidance will be updated
on a best-effort basis, but if you are working at the bleeding edge some of it
may be out of date.
```

## Config changes

- The `build-system.build-backend` key in pyproject.toml must be changed to
  `scikit_build_core.build`.
- Replace `scikit-build` with `scikit-build-core` in `build-system.requires`.
- You should remove `cmake` and `ninja` from `build-system.requires`.
  `scikit-build-core` will add these if necessary, but will respect existing
  installations of the tools by default, which allows compatibility with systems
  where binaries are not available on PyPI but can be installed from elsewhere.
  Instead, set the minimum required versions in the `[tool.scikit-build]` table:
  `cmake.minimum-required` and `ninja.minimum-required`.
- You must fill out the `tool.scikit-build` table in pyproject.toml, see
  [getting started](./getting_started.md) for more information.
- If your project is primarily configured using setup.py or setup.cfg, you will
  need to move the configuration to pyproject.toml. The
  [project metadata spec](https://packaging.python.org/en/latest/specifications/declaring-project-metadata/#declaring-project-metadata)
  shows the information that can be placed directly in the project table. For
  additional metadata, see [our configuration guide](./configuration.md). A
  useful trick for performing this migration is to change the `build-backend`
  from `skbuild` to `setuptools`, install `hatch`, and run `hatch init --new`.
  This should automatically migrate the configuration to pyproject.toml, after
  which you can change the `build-backend` to `scikit-build-core`.
- If you specify files to include in sdists via MANIFEST.in, with
  `scikit-build-core` you should now instead use the `sdist.include` and
  `sdist.exclude` fields in the `tool.scikit-build` table. Note that
  scikit-build-core uses all non `.gitignore`'d files by default, so this is
  often minimal or not needed.

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

- The UseCython CMake module distributed with scikit-build is not currently
  supported. For examples on how to use Cython, see
  [our getting started guide](./getting_started.md) for now.
- The `SKBUILD_CONFIGURE_OPTIONS` environment variable is now named
  `SKBUILD_CMAKE_ARGS` for consistency.
- The `SKBUILD_BUILD_OPTIONS` environment variable is not supported. Some
  specific features are accessible using alternative variables. In particular,
  use `CMAKE_BUILD_PARALLEL_LEVEL` or `SKBUILD_CMAKE_VERBOSE` to control build
  parallelism or CMake verbosity directly.
