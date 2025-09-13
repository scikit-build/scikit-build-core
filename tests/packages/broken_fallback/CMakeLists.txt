cmake_minimum_required(VERSION 3.15...3.26)
project(${SKBUILD_PROJECT_NAME} LANGUAGES C)

if(DEFINED BROKEN_CMAKE)
  message(FATAL_ERROR "Broken CMake")
endif()

find_package(
  Python
  COMPONENTS Interpreter Development.Module
  REQUIRED)

python_add_library(example MODULE main.c WITH_SOABI)
if(DEFINED BROKEN_CODE)
  target_compile_definitions(example PRIVATE BROKEN_CODE)
endif()

install(TARGETS example DESTINATION .)
