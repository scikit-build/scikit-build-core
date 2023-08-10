#include <pybind11/pybind11.h>

namespace py = pybind11;

PYBIND11_MODULE(sdist_config, m) {
    m.def("life", []() { return 42; });
}
