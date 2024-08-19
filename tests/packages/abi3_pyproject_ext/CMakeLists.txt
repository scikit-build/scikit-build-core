cmake_minimum_required(VERSION 3.15...3.29)

project(
  ${SKBUILD_PROJECT_NAME}
  LANGUAGES C
  VERSION ${SKBUILD_PROJECT_VERSION})

find_package(
  Python
  COMPONENTS Interpreter Development.Module ${SKBUILD_SABI_COMPONENT}
  REQUIRED)

if(NOT "${SKBUILD_SABI_COMPONENT}" STREQUAL "")
  include(CMakePrintHelpers)
  cmake_print_variables(
    Python_SABI_LIBRARY Python_SOSABI Python_SABI_LIBRARIES
    Python_SABI_LIBRARY_DIRS Python_RUNTIME_SABI_LIBRARY_DIRS)
  python_add_library(abi3_example MODULE abi3_example.c WITH_SOABI USE_SABI 3.7)
else()
  python_add_library(abi3_example MODULE abi3_example.c WITH_SOABI)
endif()

install(TARGETS abi3_example DESTINATION .)
