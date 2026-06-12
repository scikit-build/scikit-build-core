#define PY_SSIZE_T_CLEAN
#include <Python.h>

#define STRINGIFY(x) #x
#define MACRO_STRINGIFY(x) STRINGIFY(x)

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

static PyMethodDef cmake_example_methods[] = {
    {"add", add, METH_VARARGS, "Add two numbers"},
    {"subtract", subtract, METH_VARARGS, "Subtract two numbers"},
    {NULL, NULL, 0, NULL}};

static struct PyModuleDef cmake_example_module = {
    PyModuleDef_HEAD_INIT, "cmake_example", NULL, -1, cmake_example_methods};

PyMODINIT_FUNC PyInit_cmake_example(void) {
  PyObject *m = PyModule_Create(&cmake_example_module);
  if (m == NULL) {
    return NULL;
  }
#ifdef VERSION_INFO
  if (PyModule_AddStringConstant(m, "__version__",
                                 MACRO_STRINGIFY(VERSION_INFO)) < 0) {
#else
  if (PyModule_AddStringConstant(m, "__version__", "dev") < 0) {
#endif
    Py_DECREF(m);
    return NULL;
  }
  return m;
}
