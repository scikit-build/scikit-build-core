#include <nanobind/nanobind.h>

namespace nb = nanobind;

float square(float x) { return x * x; }

NB_MODULE(_core, m) { m.def("square", &square); }
