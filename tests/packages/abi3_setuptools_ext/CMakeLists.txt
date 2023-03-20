cmake_minimum_required(VERSION 3.15...3.26)

project(
  ${SKBUILD_PROJECT_NAME}
  LANGUAGES C
  VERSION ${SKBUILD_PROJECT_VERSION})

find_package(
  Python
  COMPONENTS Interpreter Development.SABIModule
  REQUIRED)

python_add_library(abi3_example MODULE abi3_example.c WITH_SOABI USE_SABI 3.7)

install(TARGETS abi3_example DESTINATION .)
