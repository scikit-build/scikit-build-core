# Authoring your CMakeLists

Scikit-build-core provides a variety of useful variables for your CMakeLists.

## Detecting Scikit-build-core

You can write CMakeLists that support running inside and outside
scikit-build-core using the `${SKBUILD}` variable. This will be defined to "2"
for scikit-build-core (and "1" for classic scikit-build). You can also detect
the version of scikit-build-core with `${SKBUILD_CORE_VERSION}`.

## Finding Python

You can directly use FindPython:

```cmake
find_package(Python COMPONENTS Interpreter Development.Module REQUIRED)
```

You always want to find at least `Interpreter` and the "Module" component of the
"Development" package. You do not want to find the entire "Development" package,
as that include "Embed" component, which is not always present and is not
related to making Python extension modules.

If you are making a Limited ABI / Stable API package, you'll need the
`Development.SABIModule` component instead.

## Finding other packages

Scikit-build-core includes the site-packages directory in CMake's search path,
so packages can provide a find package config with a name matching the package
name - such as the `pybind11` package. Later versions of scikit-build core will
include a design for package to provide arbitrary CMake code.

Third party packages can declare entry-points `cmake.module` and `cmake.prefix`,
and the specified module will be added to `CMAKE_PREFIX_PATH` and
`CMAKE_MODULE_PATH`, respectively. Currently, the key is not used, but
eventually there might be a way to request or exclude certain entry-points by
key.

## Install directories

Scikit-build-core will install directly into platlib, which will end up in
site-packages. If you are used to scikit-build, you might find targeting
`/<module_name>` to be more natural. You can mimic the old behavior with a
configuration option (`wheel.install-dir`). However, scikit-build-core is more
powerful, and allows you to install multiple packages or top-level extension
modules if you need to.

You can access all of the possible output directories, regardless of
configuration, with the variables:

- `${SKBUILD_PLATLIB_DIR}`: The original platlib directory. Anything here goes
  directly to site-packages when a wheel is installed.
- `${SKBUILD_DATA_DIR}`: The data directory. Anything here goes to the root of
  the environment when a wheel is installed (use with care).
- `${SKBUILD_HEADERS_DIR}`: The header directory. Anything in here gets
  installed to Python's header directory.
- `${SKBUILD_SCRIPTS_DIR}`: The scripts directory. Anything placed in here will
  go to `bin` (Unix) or `Scripts` (Windows).
- `${SKBUILD_NULL_DIR}`: Anything installed here will not be placed in the
  wheel.

## Future additions

Scikit-build-core does not include helpers for Fortran or Cython like
scikit-build classic yet. These will be carefully reimagined soon.
