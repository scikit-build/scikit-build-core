cmake_minimum_required(VERSION 3.15)
project(${SKBUILD_PROJECT_NAME} LANGUAGES C)

find_package(
  Python
  COMPONENTS Interpreter Development.Module
  REQUIRED)

find_program(CYTHON "cython")

add_custom_command(
  OUTPUT src/pkg1/one.c
  DEPENDS src/pkg1/one.pyx
  VERBATIM
  COMMAND "${CYTHON}" "${CMAKE_CURRENT_SOURCE_DIR}/src/pkg1/one.pyx"
          --output-file "${CMAKE_CURRENT_BINARY_DIR}/src/pkg1/one.c")

python_add_library(one MODULE "${CMAKE_CURRENT_BINARY_DIR}/src/pkg1/one.c"
                   WITH_SOABI)

install(TARGETS one DESTINATION pkg1/)
