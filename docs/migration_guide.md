# Migrating from scikit-build

```{warning}
scikit-build-core is under active development.
This guidance will be updated on a best-effort basis, but if you are working at the bleeding edge some of it may be out of date.
```


## Config changes

- The `build-system.build-backend` key in pyproject.toml must be changed to `scikit_build_core.build`.
- Replace `scikit-build` with `scikit-build-core` in `build-system.requires`.
- You may remove `cmake` and `ninja` from `build-system.requires` (IS THIS REQUIRED? CAN THESE BE LEFT IN PLACE IF DESIRED? WHAT IF STRICTER VERSIONS REQUIREMENTS ARE NEEDED THAN WHAT SCIKIT-BUILD-CORE'S CONFIG SUPPORTS?)
- You must fill out the `tool.scikit-build` table in pyproject.toml, see [getting started](./getting_started.md) for more information.

## CMake changes

scikit-build users wishing to switch to scikit-build-core should be aware of the following changes that must be made to their CMake files:


- The PythonExtensions CMake module distributed with scikit-build is not part of scikit-build-core. Due to improvement in CMake's built-in support for building Python extension modules, this module is no longer necessary. Change
```cmake
find_package(PythonExtensions REQUIRED)
add_library(${LIBRARY} MODULE ${FILENAME})
python_extension_module(${LIBRARY})
```
to
```cmake
find_package(Python COMPONENTS Interpreter Development.Module REQUIRED)
python_add_library(${LIBRARY} MODULE ${FILENAME})
```
- The UseCython CMake module distributed with scikit-build is not currently supported. For examples on how to use Cython, see [our getting started guide](./getting_started.md)
- The `SKBUILD_CONFIGURE_OPTIONS` environment variable is not yet supported. For now, using `CMAKE_ARGS` is a suitable substitute.
- The `SKBUILD_BUILD_OPTIONS` environment variable is not yet supported.
