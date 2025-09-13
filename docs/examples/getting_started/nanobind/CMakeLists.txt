cmake_minimum_required(VERSION 3.15...3.26)
project(${SKBUILD_PROJECT_NAME} LANGUAGES CXX)

find_package(Python 3.8 REQUIRED COMPONENTS Interpreter Development.Module)

find_package(nanobind CONFIG REQUIRED)

nanobind_add_module(example NB_STATIC example.cpp)

install(TARGETS example LIBRARY DESTINATION .)
