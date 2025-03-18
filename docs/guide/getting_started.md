# Getting started

If you've never made a Python package before, [packaging.python.org's
tutorial][] is a great place to start. It walks you through creating a simple
package in pure Python using modern tooling and configuration. Another great
resource is the [Scientific Python Developer Guide][]. And a tutorial can be
found at [INTERSECT Training: Packaging][].

## Quick start

There are several mechanisms to quickly get started with a package:

- [uv][] has built-in support for scikit-build-core. Just make a directory for
  your package and run: `uv init --lib --build-backend=scikit`.
- [scientific-python/cookie][] has a cookiecutter/copier template for making a
  package with all the suggestions in the [Scientific Python Developer Guide][].
- For pybind11, there's a example template at [pybind11/scikit_build_example][].
  For nanobind, [nanobind example][] includes the Stable ABI on Python 3.12+!
- There are several examples including scikit-build-core examples (including
  free-threading) at [scikit-build-sample-projects][].

## Writing an extension

We will be writing these files:

````{tab} pybind11

```
example-project
├── example.cpp
├── pyproject.toml
└── CMakeLists.txt
```

````

````{tab} nanobind

```
example-project
├── example.cpp
├── pyproject.toml
└── CMakeLists.txt
```

````

````{tab} SWIG

```
example-project
├── example.c
├── example.i
├── pyproject.toml
└── CMakeLists.txt
```

````

````{tab} Cython

```
example-project
├── example.pyx
├── pyproject.toml
└── CMakeLists.txt
```

````

````{tab} C

```
example-project
├── example.c
├── pyproject.toml
└── CMakeLists.txt
```

````

````{tab} ABI3

```
example-project
├── example.c
├── pyproject.toml
└── CMakeLists.txt
```

````

````{tab} Fortran

```
example-project
├── example.f
├── pyproject.toml
└── CMakeLists.txt
```

````

### Source code

For this tutorial, you can either write a C extension yourself, or you can use
pybind11 and C++. Select your preferred version using the tabs - compare them!

````{tab} pybind11

```{literalinclude} ../examples/getting_started/pybind11/example.cpp
:language: cpp
```

````

````{tab} nanobind

```{literalinclude} ../examples/getting_started/nanobind/example.cpp
:language: cpp
```

````

````{tab} SWIG

```{literalinclude} ../examples/getting_started/swig/example.c
:language: c
```

```{literalinclude} ../examples/getting_started/swig/example.i
:language: swig
```

````

````{tab} Cython

```{literalinclude} ../examples/getting_started/cython/example.pyx
:language: cython
```

````

````{tab} C

```{literalinclude} ../examples/getting_started/c/example.c
:language: c
```

````

````{tab} ABI3

```{literalinclude} ../examples/getting_started/abi3/example.c
:language: c
```

````

````{tab} Fortran

```{literalinclude} ../examples/getting_started/fortran/example.f
:language: fortran
```

````

### Python package configuration

To create your first compiled package, start with a pyproject.toml like this:

````{tab} pybind11

```{literalinclude} ../examples/getting_started/pybind11/pyproject.toml
:language: toml
```

````

````{tab} nanobind

```{literalinclude} ../examples/getting_started/nanobind/pyproject.toml
:language: toml
```

````

````{tab} SWIG

```{literalinclude} ../examples/getting_started/swig/pyproject.toml
:language: toml
```

````

````{tab} Cython

```{literalinclude} ../examples/getting_started/cython/pyproject.toml
:language: toml
```

````

````{tab} C

```{literalinclude} ../examples/getting_started/c/pyproject.toml
:language: toml
```

````

````{tab} ABI3

```{literalinclude} ../examples/getting_started/abi3/pyproject.toml
:language: toml
```

````

````{tab} Fortran

```{literalinclude} ../examples/getting_started/fortran/pyproject.toml
:language: toml
```

```{warning}
The module you build will require an equal or newer version to the version of
NumPy it built with. You should use `oldest-supported-numpy` or manually set
the NumPy version, though you will then be stuck with older versions of f2py.
Also it's hard to compile Fortran on Windows as it's not supported by MSVC and
macOS as it's not supported by Clang.
```


````

Notice that you _do not_ include `cmake`, `ninja`, `setuptools`, or `wheel` in
the requires list. Scikit-build-core will intelligently decide whether it needs
`cmake` and/or `ninja` based on what versions are present in the environment -
some environments can't install the Python versions of CMake and Ninja, like
Android, FreeBSD, WebAssembly, and ClearLinux, but they may already have these
tools installed. Setuptools is not used by scikit-build-core's native builder,
and wheel should never be in this list.

There are other keys you should include under `[project]` if you plan to publish
a package, but this is enough to start for now. The
[project metadata specification](https://packaging.python.org/en/latest/specifications/pyproject-toml)
page covers what keys are available. Another example is available at
[the Scientific Python Library Development Guide](https://learn.scientific-python.org/development/guides).

### CMake file

Now, you'll need a file called `CMakeLists.txt`. This one will do:

````{tab} pybind11

```{literalinclude} ../examples/getting_started/pybind11/CMakeLists.txt
:language: cmake
```

Scikit-build requires CMake 3.15, so there's no need to set it lower than 3.15.

The project line can optionally use `SKBUILD_PROJECT_NAME` and
`SKBUILD_PROJECT_VERSION` variables to avoid repeating this information from
your `pyproject.toml`. You should specify exactly what language you use to keep
CMake from searching for both `C` and `CXX` compilers (the default).

If you place find Python first, pybind11 will respect it instead of the classic
FindPythonInterp/FindPythonLibs mechanisms, which work, but are not as modern.
Here we set `PYBIND11_FINDPYTHON` to `ON` instead of doing the find Python
ourselves. Pybind11 places its config file such that CMake can find it from
site-packages.

You can either use `pybind11_add_module` or `python_add_library` and then link
to `pybind11::module`, your choice.

````

````{tab} nanobind

```{literalinclude} ../examples/getting_started/nanobind/CMakeLists.txt
:language: cmake
```

Scikit-build and nanobind require CMake 3.15, so there's no need to set it
lower than 3.15.

The project line can optionally use `SKBUILD_PROJECT_NAME` and
`SKBUILD_PROJECT_VERSION` variables to avoid repeating this information from
your `pyproject.toml`. You should specify exactly what language you use to keep
CMake from searching for both `C` and `CXX` compilers (the default).

Nanobind places its config file such that CMake can find it from site-packages.
````

````{tab} SWIG

```{literalinclude} ../examples/getting_started/swig/CMakeLists.txt
:language: cmake
```

Scikit-build requires CMake 3.15, so there's no need to set it lower than 3.15.

The project line can optionally use `SKBUILD_PROJECT_NAME` and
`SKBUILD_PROJECT_VERSION` variables to avoid repeating this information from
your `pyproject.toml`. You should specify exactly what language you use to keep
CMake from searching for both `C` and `CXX` compilers (the default).

You'll need to handle the generation of files by SWIG directly.

````

````{tab} Cython

```{literalinclude} ../examples/getting_started/cython/CMakeLists.txt
:language: cmake
```

Scikit-build requires CMake 3.15, so there's no need to set it lower than 3.15.

The project line can optionally use `SKBUILD_PROJECT_NAME` and
`SKBUILD_PROJECT_VERSION` variables to avoid repeating this information from
your `pyproject.toml`. You should specify exactly what language you use to keep
CMake from searching for both `C` and `CXX` compilers (the default).

You'll need to handle the generation of files by Cython directly at the moment.
A helper (similar to scikit-build classic) might be added in the future.

````

````{tab} C

```{literalinclude} ../examples/getting_started/c/CMakeLists.txt
:language: cmake
```

Scikit-build requires CMake 3.15, so there's no need to set it lower than 3.15.

The project line can optionally use `SKBUILD_PROJECT_NAME` and
`SKBUILD_PROJECT_VERSION` variables to avoid repeating this information from
your `pyproject.toml`. You should specify exactly what language you use to keep
CMake from searching for both `C` and `CXX` compilers (the default).

`find_package(Python ...)` should always include the `Development.Module`
component instead of `Development`; the latter breaks if the embedding
components are missing, such as when you are building redistributable wheels on
Linux.

You'll want `WITH_SOABI` when you make the module to ensure the full extension
is included on Unix systems (PyPy won't even be able to open the extension
without it).

````

````{tab} ABI3

```{literalinclude} ../examples/getting_started/abi3/CMakeLists.txt
:language: cmake
```

Scikit-build requires CMake 3.15, so there's no need to set it lower than 3.15.

The project line can optionally use `SKBUILD_PROJECT_NAME` and
`SKBUILD_PROJECT_VERSION` variables to avoid repeating this information from
your `pyproject.toml`. You should specify exactly what language you use to keep
CMake from searching for both `C` and `CXX` compilers (the default).

`find_package(Python ...)` needs `Development.SABIModule` for ABI3 extensions.

You'll want `WITH_SOABI` when you make the module. You'll also need to set the `USE_SABI`
argument to the minimum version to build with. This will also add a proper
PRIVATE define of `Py_LIMITED_API` for you.

```{note}
This will not support pypy, so you'll want to provide an alternative if you
support PyPy).
```

````

````{tab} Fortran

```{literalinclude} ../examples/getting_started/fortran/CMakeLists.txt
:language: cmake
```

Scikit-build requires CMake 3.15, so there's no need to set it lower than 3.15.

The project line can optionally use `SKBUILD_PROJECT_NAME` and
`SKBUILD_PROJECT_VERSION` variables to avoid repeating this information from
your `pyproject.toml`. You should specify exactly what language you use to keep
CMake from searching for both `C` and `CXX` compilers (the default).

You'll need to handle the generation of files by NumPy directly at the moment.
A helper (similar to scikti-build classic) might be added in the future. You'll
need gfortran on macOS.

````

Finally, you install your module. The default install path will go directly to
`site-packages`, so if you are creating anything other than a single
c-extension, you will want to install to the package directory (possibly
`${SKBUILD_PROJECT_NAME}`) instead.

### Building and installing

That's it! You can try building it:

```console
$ pipx run build
```

[pipx](https://pipx.pypa.io) allows you to install and run Python applications
in isolated environments.

Or installing it (in a virtualenv, ideally):

```console
$ pip install .
```

That's it for a basic package!

<!-- prettier-ignore-start -->
[scientific python developer guide]: https://github.com/scikit-build/scikit-build-sample-projects
[scikit-build-sample-projects]:      https://github.com/scikit-build/scikit-build-sample-projects
[uv]:                                https://docs.astral.sh/uv/
[scientific-python/cookie]:          https://github.com/scientific-python/cookie
[pybind11/scikit_build_example]:     https://github.com/pybind/scikit_build_example
[INTERSECT Training: Packaging]:     https://intersect-training.org/packaging
[packaging.python.org's tutorial]:   https://packaging.python.org/en/latest/tutorials/packaging-projects
[nanobind example]:                  https://github.com/wjakob/nanobind_example
<!-- prettier-ignore-end -->
