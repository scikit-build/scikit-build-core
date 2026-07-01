# Getting started

If you've never made a Python package before, [packaging.python.org's
tutorial][] is a great place to start. It walks you through creating a simple
package in pure Python using modern tooling and configuration. Another great
resource is the [Scientific Python Developer Guide][]. And a tutorial can be
found at [INTERSECT Training: Packaging][].

You can also find examples:

- For pybind11, there's a example template at [pybind11/scikit_build_example][].
  For nanobind, [nanobind example][] includes the Stable ABI on Python 3.12+!
- There are several examples including scikit-build-core examples (including
  free-threading) at [scikit-build-sample-projects][].

We also keep
[a list of some of the projects using scikit-build-core](../about/projects.md).

## Quick start

There are several mechanisms to quickly get started with a package:

- Scikit-build-core ships an `init` command:
  `scikit-build init --backend pybind11 myproject` scaffolds the exact project
  this page builds (run without `--backend` to pick one interactively). The rest
  of this page walks through what it generates.
- [uv][] has built-in support for scikit-build-core. Just make a directory for
  your package and run: `uv init --lib --build-backend=scikit`.
- [scientific-python/cookie][] has a cookiecutter/copier template for making a
  package with all the suggestions in the [Scientific Python Developer Guide][].
- [buildgen][] can generate Python extensions with
  `buildgen new myext -r py/pybind11` (see all with `buildgen list`, includes
  pybind11, nanobind, Cython, and C extensions).

```{versionadded} 1.0
The `scikit-build init` command.
```

For the rest of this page, however, we will show you how to get set up from
scratch.

## Writing an extension

```{tip}
The fastest way to lay these files out is `scikit-build init --backend pybind11`
(or any backend below), which generates exactly the project shown here. Read on
to understand each piece.
```

We will be writing these files:

````{tab} pybind11

```
example
├── pyproject.toml
├── CMakeLists.txt
└── src
    └── example
        ├── __init__.py
        └── _core.cpp
```

````

````{tab} nanobind

```
example
├── pyproject.toml
├── CMakeLists.txt
└── src
    └── example
        ├── __init__.py
        └── _core.cpp
```

````

````{tab} SWIG

```
example
├── pyproject.toml
├── CMakeLists.txt
└── src
    └── example
        ├── __init__.py
        ├── _core.c
        └── _core.i
```

````

````{tab} Cython

```
example
├── pyproject.toml
├── CMakeLists.txt
└── src
    └── example
        ├── __init__.py
        └── _core.pyx
```

````

````{tab} C

```
example
├── pyproject.toml
├── CMakeLists.txt
└── src
    └── example
        ├── __init__.py
        └── _core.c
```

````

````{tab} ABI3

```
example
├── pyproject.toml
├── CMakeLists.txt
└── src
    └── example
        ├── __init__.py
        └── _core.c
```

````

````{tab} ABI3t

```
example
├── pyproject.toml
├── CMakeLists.txt
└── src
    └── example
        ├── __init__.py
        └── _core.c
```

````

````{tab} Fortran

```
example
├── pyproject.toml
├── CMakeLists.txt
└── src
    └── example
        ├── __init__.py
        └── _core.f
```

````

### Source code

For this tutorial, you can either write a C extension yourself, or you can use
pybind11 and C++. Select your preferred version using the tabs - compare them!
The compiled extension is built as `_core` and lives inside the `example`
package at `src/example/_core.*`.

````{tab} pybind11

```{literalinclude} ../examples/generated/pybind11/src/example/_core.cpp
:language: cpp
```

````

````{tab} nanobind

```{literalinclude} ../examples/generated/nanobind/src/example/_core.cpp
:language: cpp
```

````

````{tab} SWIG

```{literalinclude} ../examples/generated/swig/src/example/_core.c
:language: c
```

```{literalinclude} ../examples/generated/swig/src/example/_core.i
:language: swig
```

````

````{tab} Cython

```{literalinclude} ../examples/generated/cython/src/example/_core.pyx
:language: cython
```

````

````{tab} C

```{literalinclude} ../examples/generated/c/src/example/_core.c
:language: c
```

````

````{tab} ABI3

```{literalinclude} ../examples/generated/abi3/src/example/_core.c
:language: c
```

````

````{tab} ABI3t

```{literalinclude} ../examples/generated/abi3t/src/example/_core.c
:language: c
```

````

````{tab} Fortran

```{literalinclude} ../examples/generated/fortran/src/example/_core.f
:language: fortranfixed
```

````

### Package init

The `src/example/__init__.py` re-exports the pieces of the compiled `_core`
extension you want as your public API, so users write `import example` rather
than reaching into `example._core`:

```{literalinclude} ../examples/generated/pybind11/src/example/__init__.py
:language: python
```

### Python package configuration

To create your first compiled package, start with a pyproject.toml like this:

````{tab} pybind11

```{literalinclude} ../examples/generated/pybind11/pyproject.toml
:language: toml
```

````

````{tab} nanobind

```{literalinclude} ../examples/generated/nanobind/pyproject.toml
:language: toml
```

````

````{tab} SWIG

```{literalinclude} ../examples/generated/swig/pyproject.toml
:language: toml
```

````

````{tab} Cython

```{literalinclude} ../examples/generated/cython/pyproject.toml
:language: toml
```

````

````{tab} C

```{literalinclude} ../examples/generated/c/pyproject.toml
:language: toml
```

````

````{tab} ABI3

```{literalinclude} ../examples/generated/abi3/pyproject.toml
:language: toml
```

````

````{tab} ABI3t

```{literalinclude} ../examples/generated/abi3t/pyproject.toml
:language: toml
```

````

````{tab} Fortran

```{literalinclude} ../examples/generated/fortran/pyproject.toml
:language: toml
```

```{warning}
The module you build will require an equal or newer version of NumPy at runtime
than the version it built with. The modern approach is to build against
`numpy>=2.0`; NumPy 2.0 wheels are backward-compatible at the C ABI level, so a
module built against NumPy 2.0 keeps working with older NumPy at runtime. Add a
runtime floor (in `[project]` `dependencies`) only if your code needs newer NumPy
features. Also it's hard to compile Fortran on Windows as it's not supported by
MSVC and macOS as it's not supported by Clang.
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

```{literalinclude} ../examples/generated/pybind11/CMakeLists.txt
:language: cmake
```

Scikit-build requires CMake 3.15, so there's no need to set it lower than 3.15.

The project line can optionally use `SKBUILD_PROJECT_NAME` and
`SKBUILD_PROJECT_VERSION` variables to avoid repeating this information from
your `pyproject.toml`. You should specify exactly what language you use to keep
CMake from searching for both `C` and `CXX` compilers (the default).

If you place find Python first, pybind11 will respect it instead of the older
FindPythonInterp/FindPythonLibs mechanisms, which work, but are not as modern.
Here we set `PYBIND11_FINDPYTHON` to `ON` instead of doing the find Python
ourselves. Pybind11 places its config file such that CMake can find it from
site-packages.

You can either use `pybind11_add_module` or `python_add_library` and then link
to `pybind11::module`, your choice.

````

````{tab} nanobind

```{literalinclude} ../examples/generated/nanobind/CMakeLists.txt
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

```{literalinclude} ../examples/generated/swig/CMakeLists.txt
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

```{literalinclude} ../examples/generated/cython/CMakeLists.txt
:language: cmake
```

Scikit-build requires CMake 3.15, so there's no need to set it lower than 3.15.

The project line can optionally use `SKBUILD_PROJECT_NAME` and
`SKBUILD_PROJECT_VERSION` variables to avoid repeating this information from
your `pyproject.toml`. You should specify exactly what language you use to keep
CMake from searching for both `C` and `CXX` compilers (the default).

[cython-cmake][] provides the `cython_transpile` helper (via `include(UseCython)`)
that turns your `.pyx` file into a C source you can pass to `python_add_library`.
Add it to your build requirements as shown in the pyproject.toml above.

````

````{tab} C

```{literalinclude} ../examples/generated/c/CMakeLists.txt
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

```{literalinclude} ../examples/generated/abi3/CMakeLists.txt
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

````{tab} ABI3t

```{versionadded} 1.0
The free-threaded Stable ABI (`abi3t`) and the combined `cp315.cp315t` tag.
```

```{literalinclude} ../examples/generated/abi3t/CMakeLists.txt
:language: cmake
```

The free-threaded Stable ABI (`abi3t`, PEP 803) is requested with
`wheel.py-api = "cp315.cp315t"`. Since `abi3t` is a subset of `abi3`, a single
free-threaded build emits the combined `cp315-abi3.abi3t` tag and loads on
every CPython 3.15+, free-threaded or not; a GIL build falls back to
`cp315-abi3`.

`USE_SABI` is set from `${SKBUILD_SABI_VERSION}` (3.15 for `abi3t`) rather than
hardcoded. CMake before 4.4 has no `abi3t` awareness, so the SOABI suffix is
taken from `${SKBUILD_SOABI}` and `Py_TARGET_ABI3T` is defined manually; both
become unnecessary on CMake 4.4+.

```{note}
`abi3t` requires CPython 3.15+ and the PEP 793 module export mechanism, so the
classic single-phase `PyInit_` entry point cannot be used.
```

````

````{tab} Fortran

```{literalinclude} ../examples/generated/fortran/CMakeLists.txt
:language: cmake
```

Scikit-build requires CMake 3.15, so there's no need to set it lower than 3.15.

The project line can optionally use `SKBUILD_PROJECT_NAME` and
`SKBUILD_PROJECT_VERSION` variables to avoid repeating this information from
your `pyproject.toml`. You should specify exactly what language you use to keep
CMake from searching for both `C` and `CXX` compilers (the default).

[f2py-cmake][] provides the `f2py_add_module` helper (via `include(UseF2Py)`)
that generates the f2py wrappers, builds the `fortranobject` support code, and
links it all into an importable module in a single call. Add it to your build
requirements as shown in the pyproject.toml above. You'll need gfortran on macOS.

````

Finally, you install your module. The `install(...)` line above targets the
`${SKBUILD_PROJECT_NAME}` package directory rather than `site-packages`
directly, which is what you want for a `src/example/` package layout - the
compiled `_core` lands next to `__init__.py`. A bare install (`DESTINATION .`)
would instead drop a single top-level extension into `site-packages`.

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
[INTERSECT Training: Packaging]:     https://intersect-training.org/packaging
[buildgen]:                          https://github.com/shakfu/buildgen
[cython-cmake]:                      https://github.com/scikit-build/cython-cmake
[f2py-cmake]:                        https://github.com/scikit-build/f2py-cmake
[nanobind example]:                  https://github.com/wjakob/nanobind_example
[packaging.python.org's tutorial]:   https://packaging.python.org/en/latest/tutorials/packaging-projects
[pybind11/scikit_build_example]:     https://github.com/pybind/scikit_build_example
[scientific python developer guide]: https://learn.scientific-python.org/development
[scientific-python/cookie]:          https://github.com/scientific-python/cookie
[scikit-build-sample-projects]:      https://github.com/scikit-build/scikit-build-sample-projects
[uv]:                                https://docs.astral.sh/uv/
<!-- prettier-ignore-end -->
