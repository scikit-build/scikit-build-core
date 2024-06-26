cmake_minimum_required(VERSION 3.15...3.29)
project(${SKBUILD_PROJECT_NAME} LANGUAGES C)

find_package(
  Python
  COMPONENTS Interpreter Development.Module
  REQUIRED)

add_custom_command(
  OUTPUT "${CMAKE_CURRENT_BINARY_DIR}/src/pkg1/one.c"
  MAIN_DEPENDENCY "${CMAKE_CURRENT_SOURCE_DIR}/src/pkg1/one.pyx"
  VERBATIM
  COMMAND
    Python::Interpreter -m cython
    "${CMAKE_CURRENT_SOURCE_DIR}/src/pkg1/one.pyx" --output-file
    "${CMAKE_CURRENT_BINARY_DIR}/src/pkg1/one.c")

python_add_library(one MODULE "${CMAKE_CURRENT_BINARY_DIR}/src/pkg1/one.c"
                   WITH_SOABI)

install(TARGETS one DESTINATION pkg1/)
