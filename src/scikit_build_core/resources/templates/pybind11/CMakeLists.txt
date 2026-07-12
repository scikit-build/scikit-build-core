cmake_minimum_required(VERSION 3.15...4.4)
project(${SKBUILD_PROJECT_NAME} LANGUAGES CXX)

set(PYBIND11_FINDPYTHON ON)
find_package(pybind11 CONFIG REQUIRED)

pybind11_add_module(_core src/${SKBUILD_PROJECT_NAME}/_core.cpp)

install(TARGETS _core LIBRARY DESTINATION ${SKBUILD_PROJECT_NAME})
