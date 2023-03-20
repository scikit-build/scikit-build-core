cmake_minimum_required(VERSION 3.15...3.26)
project(${SKBUILD_PROJECT_NAME} LANGUAGES C)

find_package(
  Python
  COMPONENTS Interpreter Development.SABIModule
  REQUIRED)

python_add_library(example MODULE example.c WITH_SOABI USE_SABI 3.7)

install(TARGETS example DESTINATION .)
