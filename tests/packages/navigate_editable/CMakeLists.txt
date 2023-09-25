cmake_minimum_required(VERSION 3.15...3.26)

project(
  ${SKBUILD_PROJECT_NAME}
  LANGUAGES C
  VERSION ${SKBUILD_PROJECT_VERSION})

find_package(Python COMPONENTS Interpreter Development.Module)

python_add_library(c_module MODULE src/shared_pkg/c_module.c WITH_SOABI)

install(
  TARGETS c_module
  DESTINATION shared_pkg/
  COMPONENT PythonModule)
