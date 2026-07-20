#define PY_SSIZE_T_CLEAN
#include <Python.h>

#include "staged_install_example.h"

static struct PyModuleDef staged_module = {
    PyModuleDef_HEAD_INIT, "staged_install_example", NULL, -1, NULL};

PyMODINIT_FUNC PyInit_staged_install_example(void) {
  PyObject *m = PyModule_Create(&staged_module);
  if (m != NULL && PyModule_AddIntMacro(m, STAGED_ANSWER) < 0) {
    Py_DECREF(m);
    return NULL;
  }
  return m;
}
