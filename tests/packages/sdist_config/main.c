#define PY_SSIZE_T_CLEAN
#include <Python.h>

#include "dummy.h"

static PyObject *life(PyObject *self, PyObject *args) {
  return PyLong_FromLong(DUMMY_LIFE);
}

static PyMethodDef sdist_config_methods[] = {
    {"life", life, METH_NOARGS, "The answer"}, {NULL, NULL, 0, NULL}};

static struct PyModuleDef sdist_config_module = {
    PyModuleDef_HEAD_INIT, "sdist_config", NULL, -1, sdist_config_methods};

PyMODINIT_FUNC PyInit_sdist_config(void) {
  return PyModule_Create(&sdist_config_module);
}
