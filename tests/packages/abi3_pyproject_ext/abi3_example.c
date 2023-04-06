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

static PyMethodDef abi3_example_methods[] = {
    {"square", square_wrapper, METH_VARARGS, "Square function"},
    {NULL, NULL, 0, NULL}};

static struct PyModuleDef abi3_example_module = {PyModuleDef_HEAD_INIT, "abi3_example",
                                             NULL, -1, abi3_example_methods};

PyMODINIT_FUNC PyInit_abi3_example(void) {
  return PyModule_Create(&abi3_example_module);
}
