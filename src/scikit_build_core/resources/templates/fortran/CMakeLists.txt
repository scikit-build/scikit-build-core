cmake_minimum_required(VERSION 3.17...3.29)
project(${SKBUILD_PROJECT_NAME} LANGUAGES C Fortran)

find_package(
  Python
  COMPONENTS Interpreter Development.Module NumPy
  REQUIRED)

include(UseF2Py)

f2py_add_module(_core src/${SKBUILD_PROJECT_NAME}/_core.f)

install(TARGETS _core DESTINATION ${SKBUILD_PROJECT_NAME})
