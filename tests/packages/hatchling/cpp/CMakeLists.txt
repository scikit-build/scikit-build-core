cmake_minimum_required(VERSION 3.15...3.26)
project(extensionlib_example_cmake LANGUAGES CXX)

set(PYBIND11_FINDPYTHON ON)
find_package(pybind11 CONFIG REQUIRED)

pybind11_add_module(_core MODULE example.cpp)
install(TARGETS _core DESTINATION .)
