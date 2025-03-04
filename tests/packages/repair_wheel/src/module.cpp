#define PY_SSIZE_T_CLEAN
#include <Python.h>

#include <base.h>

static PyObject *hello(PyObject *self, PyObject *args){
  base::hello();
  Py_RETURN_NONE;
}

static PyMethodDef repair_wheel_methods[] = {
    {"hello", hello, METH_NOARGS, "Say hello"},
    {NULL, NULL, 0, NULL}};

static struct PyModuleDef repair_wheel_module = {PyModuleDef_HEAD_INIT, "_module",
                                             NULL, -1, repair_wheel_methods};

PyMODINIT_FUNC PyInit__module(void) {
    return PyModule_Create(&repair_wheel_module);
}
