cmake_minimum_required(VERSION 3.15...3.26)
project(${SKBUILD_PROJECT_NAME} LANGUAGES C)

find_package(
  Python
  COMPONENTS Interpreter Development.Module
  REQUIRED)

add_custom_command(
  OUTPUT example.c
  COMMENT
    "Making ${CMAKE_CURRENT_BINARY_DIR}/example.c from ${CMAKE_CURRENT_SOURCE_DIR}/example.pyx"
  COMMAND Python::Interpreter -m cython
          "${CMAKE_CURRENT_SOURCE_DIR}/example.pyx" --output-file example.c
  DEPENDS example.pyx
  VERBATIM)

python_add_library(example MODULE example.c WITH_SOABI)

install(TARGETS example DESTINATION .)
