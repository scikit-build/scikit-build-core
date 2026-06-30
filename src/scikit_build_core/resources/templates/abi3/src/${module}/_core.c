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

static PyMethodDef _core_methods[] = {
    {"square", square_wrapper, METH_VARARGS, "Square function"},
    {NULL, NULL, 0, NULL}};

static struct PyModuleDef _core_module = {PyModuleDef_HEAD_INIT, "_core", NULL,
                                          -1, _core_methods};

/* name here must match extension name, with PyInit_ prefix */
PyMODINIT_FUNC PyInit__core(void) { return PyModule_Create(&_core_module); }
