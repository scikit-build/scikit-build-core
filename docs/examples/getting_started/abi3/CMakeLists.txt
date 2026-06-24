cmake_minimum_required(VERSION 3.15...4.3)
project(${SKBUILD_PROJECT_NAME} LANGUAGES C)

find_package(
  Python
  COMPONENTS Interpreter Development.SABIModule
  REQUIRED)

python_add_library(example MODULE example.c WITH_SOABI USE_SABI 3.8)

install(TARGETS example DESTINATION .)
