cmake_minimum_required(VERSION 3.15...3.26)
project(${SKBUILD_PROJECT_NAME} LANGUAGES C)

find_package(
  Python
  COMPONENTS Interpreter Development.Module
  REQUIRED)

find_program(CYTHON "cython")

file(MAKE_DIRECTORY "${CMAKE_CURRENT_BUILD_DIR}")
add_custom_command(
  OUTPUT example.c
  COMMAND "${CYTHON}" "${CMAKE_CURRENT_SOURCE_DIR}/example.pyx" --output-file
          example.c
  DEPENDS example.pyx
  VERBATIM)

python_add_library(example MODULE example.c WITH_SOABI)

install(TARGETS example DESTINATION .)
