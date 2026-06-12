#define PY_SSIZE_T_CLEAN
#include <Python.h>

static PyObject *add(PyObject *self, PyObject *args) {
  int i, j;
  if (!PyArg_ParseTuple(args, "ii", &i, &j)) {
    return NULL;
  }
  return PyLong_FromLong((long)i + (long)j);
}

static PyObject *subtract(PyObject *self, PyObject *args) {
  int i, j;
  if (!PyArg_ParseTuple(args, "ii", &i, &j)) {
    return NULL;
  }
  return PyLong_FromLong((long)i - (long)j);
}

static PyMethodDef core_methods[] = {
    {"add", add, METH_VARARGS, "Add two numbers"},
    {"subtract", subtract, METH_VARARGS, "Subtract two numbers"},
    {NULL, NULL, 0, NULL}};

static struct PyModuleDef core_module = {PyModuleDef_HEAD_INIT, "_core", NULL,
                                         -1, core_methods};

PyMODINIT_FUNC PyInit__core(void) { return PyModule_Create(&core_module); }
