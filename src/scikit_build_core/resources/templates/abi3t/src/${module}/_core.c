#define PY_SSIZE_T_CLEAN
#include <Python.h>

/* Free-threaded Stable ABI (abi3t, PEP 803) example. abi3t requires the
 * PEP 793 module-export mechanism: with the opaque PyObject it enables, the
 * classic static PyModuleDef cannot be used. abi3t is a subset of abi3, so a
 * single build loads on both free-threaded and GIL-enabled CPython 3.15+. */

static float square(float x) { return x * x; }

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

PyABIInfo_VAR(_core_abi_info);

/* name here must match extension name, with PyModExport_ prefix */
PyMODEXPORT_FUNC PyModExport__core(void) {
  static PySlot slots[] = {
      PySlot_DATA(Py_mod_abi, &_core_abi_info),
      PySlot_STATIC_DATA(Py_mod_name, "_core"),
      PySlot_STATIC_DATA(Py_mod_methods, _core_methods),
      PySlot_DATA(Py_mod_gil, Py_MOD_GIL_NOT_USED),
      PySlot_END,
  };
  return slots;
}
