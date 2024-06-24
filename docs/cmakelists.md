# Authoring your CMakeLists

Scikit-build-core provides a variety of useful variables for your CMakeLists.

## Detecting Scikit-build-core

You can write CMakeLists that support running inside and outside
scikit-build-core using the `${SKBUILD}` variable. This will be defined to "2"
for scikit-build-core (and "1" for classic scikit-build). You can also detect
the version of scikit-build-core with `${SKBUILD_CORE_VERSION}`.

## Accessing information

Scikit-build-core provides several useful variables:

- `${SKBUILD_PROJECT_NAME}`: The name of the project.
- `${SKBUILD_PROJECT_VERSION}`: The version of the project in a form CMake can
  use.
- `${SKBUILD_PROJECT_VERSION_FULL}`: The exact version of the project including
  dev & local suffix.
- `${SKBUILD_STATE}`: The run state, one of `sdist`, `wheel`, `metadata_wheel`,
  `editable`, or `metadata_editable`.

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
`Development.SABIModule` component instead (CMake 3.26+). You can use the
`SKBUILD_LIMITED_API` variable to check to see if it was requested.

<!-- prettier-ignore-start -->
:::{warning}
:name: soabi

If you want to cross-compile to Windows ARM, you'll need to use
`${SKBUILD_SOABI}`, which is always correct, instead of trusting FindPython's
`Python_SOABI` value. You can manually set the extension suffix after making a
target:

```cmake
if(CMAKE_SYSTEM_NAME STREQUAL "Windows")
    set_property (TARGET ${name} PROPERTY SUFFIX ".${SKBUILD_SOABI}.pyd")
else()
    set_property (TARGET ${name} PROPERTY SUFFIX ".${SKBUILD_SOABI}${CMAKE_SHARED_MODULE_SUFFIX}")
endif()
```
<!-- prettier-ignore-end -->

A quicker way to do this would be to instead override `Python_SOABI` after
`find_package(Python)`:

```cmake
set(Python_SOABI ${SKBUILD_SOABI})
```

However, this isn't officially supported upstream, and only works due to the way
this variable is used when creating targets.

:::

If you want to use the old, deprecated FindPythonInterp and FindPythonLibs
instead, you can. Though it should be noted that FindPythonLibs requires a trick
to make it work properly if a Python library is not preset (like in manylinux):
you have to set `PYTHON_LIBRARY` to something (doesn't matter what) to make it
succeed.

## Finding other packages

Scikit-build-core includes the site-packages directory in CMake's search path,
so packages can provide a find package config with a name matching the package
name - such as the `pybind11` package.

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
- `${SKBUILD_METADATA_DIR}`: The dist-info directory. Licenses go in the
  `licenses` subdirectory. _Note that CMake is not run in the
  `prepare_metadata_\*` hooks, so anything written to this directory will only
  be present when writing wheels.\_
- `${SKBUILD_NULL_DIR}`: Anything installed here will not be placed in the
  wheel.

## Limited API / Stable ABI

You can activate the limited ABI by setting When you do that,
`${SKBUILD_SABI_COMPONENT}` will be set to `Development.SABIModule` if you can
target this (new enough CPython), and will remain an empty string otherwise
(PyPy). This allows the following idiom:

```cmake
find_package(Python REQUIRED COMPONENTS Interpreter Development.Module ${SKBUILD_SABI_COMPONENT})
```

This will add this only if scikit-build-core is driving the compilation and is
targeting ABI3. If you want to support limited ABI from outside
scikit-build-core, look into the `OPTIONAL_COMPONENTS` flag for `find_package`.

When defining your module, if you only support the Stable ABI after some point,
you should use (for example for 3.11):

```cmake
if(NOT "${SKBUILD_SABI_COMPONENT}" STREQUAL "")
  python_add_library(some_ext MODULE WITH_SOABI USE_SABI 3.11 ...)
else()
  python_add_library(some_ext MODULE WITH_SOABI ...)
endif()
```

This will define `Py_LIMITED_API` for you. If you want to support building
directly from CMake, you need to protect this for Python version,
`Python_INTERPRETER_ID STREQUAL Python`, and free-threading Python 3.13+ doesn't
support ABI3 either.

If you are using `nanobind`'s `nanobind_add_module`, the `STABLE_ABI` flag does
this automatically for you for 3.12+.

## Future additions

Scikit-build-core does not include helpers for F2Py or Cython like scikit-build
classic yet. These will be carefully reimagined soon.
