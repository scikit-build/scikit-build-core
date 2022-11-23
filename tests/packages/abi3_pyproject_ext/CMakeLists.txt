cmake_minimum_required(VERSION 3.15...3.25)

project(
  ${SKBUILD_PROJECT_NAME}
  LANGUAGES C
  VERSION ${SKBUILD_PROJECT_VERSION})

find_package(Python COMPONENTS Interpreter Development.Module)
set(Python_SOABI ${SKBUILD_SOABI})

python_add_library(abi3_example MODULE abi3_example.c WITH_SOABI)

install(TARGETS abi3_example DESTINATION .)
