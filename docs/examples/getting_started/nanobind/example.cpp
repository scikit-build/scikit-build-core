#include <nanobind/nanobind.h>

namespace nb = nanobind;

float square(float x) { return x * x; }

NB_MODULE(example, m) {
    m.def("square", &square);
}
