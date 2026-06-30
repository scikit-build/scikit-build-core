cmake_minimum_required(VERSION 3.17...4.3)
project(${SKBUILD_PROJECT_NAME} LANGUAGES C Fortran)

find_package(
  Python
  COMPONENTS Interpreter Development.Module NumPy
  REQUIRED)

include(UseF2Py)

f2py_add_module(example example.f)

install(TARGETS example DESTINATION .)
