cmake_minimum_required(VERSION 3.15...4.4)
project(
  "${SKBUILD_PROJECT_NAME}"
  LANGUAGES C
  VERSION "${SKBUILD_PROJECT_VERSION}")

find_package(
  Python
  COMPONENTS Interpreter Development.Module
  REQUIRED)

python_add_library(cmake_example MODULE main.c WITH_SOABI)

target_compile_definitions(cmake_example
                           PRIVATE VERSION_INFO=${PROJECT_VERSION})

install(TARGETS cmake_example LIBRARY DESTINATION .)
