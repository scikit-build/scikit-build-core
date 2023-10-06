#define PY_SSIZE_T_CLEAN
#include <Python.h>
#include <stdio.h>
#include <stdlib.h>

const char* c_method() { return "c_method"; }

static PyObject *c_method_wrapper(PyObject *self, PyObject *args) {
  return PyUnicode_FromString(c_method());
}

static PyObject *py_method_wrapper(PyObject *self, PyObject *args) {
  PyObject *py_module = PyImport_ImportModule("shared_pkg.py_module");
  if (py_module == NULL) {
    PyErr_Print();
    fprintf(stderr, "Failed to load shared_pkg.py_module\n");
    exit(1);
  }
  PyObject *py_method = PyObject_GetAttrString(py_module,(char*)"py_method");
  if (py_method == NULL) {
    PyErr_Print();
    fprintf(stderr, "Failed to load shared_pkg.py_module.py_method\n");
    exit(1);
  }

#if PY_MAJOR_VERSION == 3 && PY_MINOR_VERSION > 8
  PyObject *res = PyObject_CallNoArgs(py_method);
#else
  PyObject *res = PyObject_CallObject(py_method, NULL);
#endif

  if (res == NULL) {
    PyErr_Print();
    fprintf(stderr, "Failed to execute shared_pkg.py_module.py_method\n");
    exit(1);
  }

  Py_DECREF(py_module);
  Py_DECREF(py_method);
  Py_DECREF(res);
  Py_RETURN_NONE;
}

static PyMethodDef c_module_methods[] = {
    {"c_method", c_method_wrapper, METH_NOARGS, "C native method"},
    {"call_py_method", py_method_wrapper, METH_NOARGS, "Call python native method"},
    {NULL, NULL, 0, NULL}};

static struct PyModuleDef c_module = {PyModuleDef_HEAD_INIT, "c_module",
                                             NULL, -1, c_module_methods};

PyMODINIT_FUNC PyInit_c_module(void) {
  return PyModule_Create(&c_module);
}
