# Getting started

If you've never made a Python package before,
[packaging.python.org's tutorial](https://packaging.python.org/en/latest/tutorials/packaging-projects/)
is a great place to start. It walks you through creating a simple package in
pure Python using modern tooling and configuration.

## Writing an extension

We will be writing these files:

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

````{tab} pybind11

```
example-project
├── example.cpp
├── pyproject.toml
└── CMakeLists.txt
```

````

### Source code

For this tutorial, you can either use write a C extension yourself, or you can
use pybind11 and C++. Select your preferred version using the tabs - compare
them!

````{tab} C

```c
#define PY_SSIZE_T_CLEAN
#include <Python.h>

float square(float x) { return x * x; }

static PyObject *square_wrapper(PyObject *self, PyObject *args) {
  float input, result;
  if (!PyArg_ParseTuple(args, "f", &input)) {
    return NULL;
  }
  result = square(input);
  return PyFloat_FromDouble(result);
}

static PyMethodDef pysimple_methods[] = {
    {"square", square_wrapper, METH_VARARGS, "Square function"},
    {NULL, NULL, 0, NULL}};

static struct PyModuleDef pysimple_module = {PyModuleDef_HEAD_INIT, "pysimple",
                                             NULL, -1, pysimple_methods};

/* name here must match extension name, with PyInit_ prefix */
PyMODINIT_FUNC PyInit_example(void) {
  return PyModule_Create(&pysimple_module);
}
```

````

````{tab} ABI3

```c
#define PY_SSIZE_T_CLEAN
#include <Python.h>

float square(float x) { return x * x; }

static PyObject *square_wrapper(PyObject *self, PyObject *args) {
  float input, result;
  if (!PyArg_ParseTuple(args, "f", &input)) {
    return NULL;
  }
  result = square(input);
  return PyFloat_FromDouble(result);
}

static PyMethodDef pysimple_methods[] = {
    {"square", square_wrapper, METH_VARARGS, "Square function"},
    {NULL, NULL, 0, NULL}};

static struct PyModuleDef pysimple_module = {PyModuleDef_HEAD_INIT, "pysimple",
                                             NULL, -1, pysimple_methods};

/* name here must match extension name, with PyInit_ prefix */
PyMODINIT_FUNC PyInit_example(void) {
  return PyModule_Create(&pysimple_module);
}
```

````

````{tab} pybind11

```cpp
#include <pybind11/pybind11.h>

namespace py = pybind11;

float square(float x) { return x * x; }

PYBIND11_MODULE(example, m) {
    m.def("square", &square);
}
```

````

### Python package configuration

To create your first compiled package, start with a pyproject.toml like this:

````{tab} C

```toml
[build-system]
requires = ["scikit-build-core"]
build-backend = "scikit_build_core.build"

[project]
name = "example"
version = "0.0.1"
```

````

````{tab} ABI3

```toml
[build-system]
requires = ["scikit-build-core"]
build-backend = "scikit_build_core.build"

[project]
name = "example"
version = "0.0.1"

[tool.scikit-build-core]
wheel.py-api = "cp37"
```

````

````{tab} pybind11

```toml
[build-system]
requires = ["scikit-build-core", "pybind11"]
build-backend = "scikit_build_core.build"

[project]
name = "example"
version = "0.0.1"
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
[project metadata specification](https://packaging.python.org/en/latest/specifications/declaring-project-metadata)
page covers what keys are available. Another example is available at
[the Scikit-HEP Developer Pages](https://scikit-hep.org/developer/pep621).

### CMake file

Now, you'll need a CMake file. This one will do:

````{tab} C

```cmake
cmake_minimum_required(VERSION 3.15...3.26)
project(${SKBUILD_PROJECT_NAME} LANGUAGES C)


find_package(Python COMPONENTS Interpreter Development.Module REQUIRED)

Python_add_library(example MODULE example.c WITH_SOABI)

install(TARGETS example DESTINATION .)
```

Scikit-build requires CMake 3.15, so there's no need to set it lower than 3.15.

The project line can optionally use `SKBUILD_PROJECT_NAME` and
`SKBUILD_PROJECT_VERSION` variables to avoid repeating this information from
your `pyproject.toml`. You should specify exactly what language you use to keep
CMake from searching for both `C` and `CXX` compilers (the default).

`find_package(Python ...)` should always include the `Development.Module`
component instead of `Developement`; the latter breaks if the embedding
components are missing, such as when you are building redistributable wheels on
Linux.

You'll want `WITH_SOABI` when you make the module to ensure the full extension
is included on Unix systems (PyPy won't even be able to open the extension
without it).

````

````{tab} ABI3

```cmake
cmake_minimum_required(VERSION 3.15...3.26)
project(${SKBUILD_PROJECT_NAME} LANGUAGES C)


find_package(Python COMPONENTS Interpreter Development.SABIModule REQUIRED)

Python_add_library(example MODULE example.c WITH_SOABI USE_SABI 3.7)

install(TARGETS example DESTINATION .)
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

````{tab} pybind11

```cmake
cmake_minimum_required(VERSION 3.15...3.26)
project(${SKBUILD_PROJECT_NAME} LANGUAGES CXX)

set(PYBIND11_NEWPYTHON ON)
find_package(pybind11 CONFIG REQUIRED)

pybind11_add_module(example example.cpp)

install(TARGETS example LIBRARY DESTINATION .)
```

Scikit-build requires CMake 3.15, so there's no need to set it lower than 3.15.

The project line can optionally use `SKBUILD_PROJECT_NAME` and
`SKBUILD_PROJECT_VERSION` variables to avoid repeating this information from
your `pyproject.toml`. You should specify exactly what language you use to keep
CMake from searching for both `C` and `CXX` compilers (the default).

If you place find Python first, pybind11 will resepct it instead of the classic
FindPythonInterp/FindPythonLibs mechanisms, which work, but are not as modern.
Here we set `PYBIND11_NEWPYTHON` to `ON` instead of doing the find Python
ourselves. Pybind11 places it's config file such that CMake can find it from
site-packages.

You can either use `pybind11_add_module` or `python_add_library` and then link
to `pybind11::module`, your choice.

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

Or installing it (in a virtualenv, ideally):

```console
$ pip install .
```

That's it for a basic package!
