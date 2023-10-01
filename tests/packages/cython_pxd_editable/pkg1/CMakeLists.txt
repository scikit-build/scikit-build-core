cmake_minimum_required(VERSION 3.15)
project(${SKBUILD_PROJECT_NAME} LANGUAGES C)

find_package(
  Python
  COMPONENTS Interpreter Development.Module
  REQUIRED)

find_program(CYTHON "cython")

add_custom_command(
  OUTPUT pkg1/one.c
  DEPENDS pkg1/one.pyx
  VERBATIM
  COMMAND "${CYTHON}" "${CMAKE_CURRENT_SOURCE_DIR}/pkg1/one.pyx" --output-file
          "${CMAKE_CURRENT_BINARY_DIR}/pkg1/one.c")

python_add_library(one MODULE "${CMAKE_CURRENT_BINARY_DIR}/pkg1/one.c"
                   WITH_SOABI)

install(TARGETS one DESTINATION pkg1/)
