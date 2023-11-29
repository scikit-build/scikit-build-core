cmake_minimum_required(VERSION 3.15)
project(${SKBUILD_PROJECT_NAME} LANGUAGES C)

find_package(
  Python
  COMPONENTS Interpreter Development.Module
  REQUIRED)

find_program(CYTHON "cython")

add_custom_command(
  OUTPUT src/pkg2/two.c
  DEPENDS src/pkg2/two.pyx
  VERBATIM
  COMMAND "${CYTHON}" "${CMAKE_CURRENT_SOURCE_DIR}/src/pkg2/two.pyx"
          --output-file "${CMAKE_CURRENT_BINARY_DIR}/src/pkg2/two.c")

python_add_library(two MODULE "${CMAKE_CURRENT_BINARY_DIR}/src/pkg2/two.c"
                   WITH_SOABI)

install(TARGETS two DESTINATION pkg2/)
