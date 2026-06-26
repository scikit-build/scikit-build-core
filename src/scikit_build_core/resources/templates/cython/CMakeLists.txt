cmake_minimum_required(VERSION 3.15...4.3)
project(${SKBUILD_PROJECT_NAME} LANGUAGES C)

find_package(
  Python
  COMPONENTS Interpreter Development.Module
  REQUIRED)
find_package(Cython MODULE REQUIRED VERSION 3.0)
include(UseCython)

cython_transpile(src/${SKBUILD_PROJECT_NAME}/_core.pyx LANGUAGE C
                 OUTPUT_VARIABLE _core_c)

python_add_library(_core MODULE "${_core_c}" WITH_SOABI)

install(TARGETS _core DESTINATION ${SKBUILD_PROJECT_NAME})
