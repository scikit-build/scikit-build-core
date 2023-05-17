cmake_minimum_required(VERSION 3.15...3.26)
project("${SKBUILD_PROJECT_NAME}" LANGUAGES CXX)

find_package(pybind11 CONFIG REQUIRED)
pybind11_add_module(_core src/main.cpp)

install(TARGETS _core LIBRARY DESTINATION mixed_setuptools)
