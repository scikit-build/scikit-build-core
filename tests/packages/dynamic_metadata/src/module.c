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

static struct PyModuleDef pysimple_module = {PyModuleDef_HEAD_INIT, "_module",
                                             NULL, -1, pysimple_methods};

PyMODINIT_FUNC PyInit__module(void) {
  return PyModule_Create(&pysimple_module);
}
