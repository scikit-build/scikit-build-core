cmake_minimum_required(VERSION 3.15...4.3)
project(${SKBUILD_PROJECT_NAME} LANGUAGES C)

find_package(
  Python
  COMPONENTS Interpreter Development.Module
  REQUIRED)
find_package(Cython MODULE REQUIRED VERSION 3.0)
include(UseCython)

cython_transpile(example.pyx LANGUAGE C OUTPUT_VARIABLE example_c)

python_add_library(example MODULE "${example_c}" WITH_SOABI)

install(TARGETS example DESTINATION .)
