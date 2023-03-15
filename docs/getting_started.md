# Getting started

If you've never made a Python package before,
[packaging.python.org's tutorial](https://packaging.python.org/en/latest/tutorials/packaging-projects/)
is a great place to start. It walks you through creating a simple package in
pure Python using modern tooling and configuration.

## Simple C Extension

We will be writing these files:

```
example-project
 - example.c
 - pyproject.toml
 - CMakeLists.txt
```

### Source code

For this tutorial, we'll assume a single C module. Don't worry! For real code,
you should usually prefer a binding tool like pybind11 to handle memory, API
changes every version, and boilerplate. We'll show a pybind11 example at the
end, too, which will look much simpler.

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

### Python package configuration

To create your first compiled package, start with a pyproject.toml like this:

```toml
[build-system]
requires = ["scikit-build-core"]
build-backend = "scikit_build_core.build"

[project]
name = "example"
version = "0.0.1"
```

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

Finally, you add your library, and install it. You'll want `WITH_SOABI` to
ensure the full extension is included on Unix systems (PyPy won't even be able
to open the extension without it). The default install path will go directly to
`site-packages`, so if you are creating anything other than a single
c-extension, you will want to install to `SKBUILD_PROJECT_NAME` instead.

That's it! You can try building it:

```console
$ pipx run build
```

Or installing it (in a virtualenv, ideally):

```console
$ pip install .
```

## Pybind11

We can modify our above files to support pybind11 instead:

```cpp
#include <pybind11/pybind11.h>

int add(int i, int j) {
    return i + j;
}

namespace py = pybind11;

PYBIND11_MODULE(example, m) {
    m.def("add", &add);
    m.def("subtract", [](int i, int j) { return i - j; });
}
```

And `pypproject.toml`:

```toml
[build-system]
requires = ["scikit-build-core", "pybind11"]
build-backend = "scikit_build_core.build"

[project]
name = "example"
version = "0.0.1"
```

Pybind11 places it's config file such that CMake can find it from site-packages.

And CMake file:

```cmake
cmake_minimum_required(VERSION 3.15...3.26)
project(${SKBUILD_PROJECT_NAME} LANGUAGES CXX)

find_package(Python COMPONENTS Interpreter Development.Module REQUIRED)
find_package(pybind11 CONFIG REQUIRED)

pybind11_add_module(example example.cpp)

install(TARGETS example LIBRARY DESTINATION .)
```

It is recommended to find Python first, so pybind11 can use FindPython, if you
remove it, pybind11 defaults to the classic FindPythonInterp/FindPythonLibs
mechanisms, which work, but are not as modern. You can eitehr use
`pybind11_add_module` or `python_add_library` and then link to
`pybind11::module`, your choice.
