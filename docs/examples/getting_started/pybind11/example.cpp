#include <pybind11/pybind11.h>

namespace py = pybind11;

float square(float x) { return x * x; }

PYBIND11_MODULE(example, m) {
    m.def("square", &square);
}
