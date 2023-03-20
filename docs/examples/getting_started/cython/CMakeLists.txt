cmake_minimum_required(VERSION 3.15...3.26)
project(${SKBUILD_PROJECT_NAME} LANGUAGES C)

find_package(
  Python
  COMPONENTS Interpreter Development.Module
  REQUIRED)

find_program(CYTHON "cython")

add_custom_command(
  OUTPUT example.c
  DEPENDS example.pyx
  VERBATIM
  COMMAND "${CYTHON}" "${CMAKE_CURRENT_SOURCE_DIR}/example.pyx" --output-file
          "${CMAKE_CURRENT_BINARY_DIR}/example.c")

python_add_library(example MODULE "${CMAKE_CURRENT_BINARY_DIR}/example.c"
                   WITH_SOABI)

install(TARGETS example DESTINATION .)
