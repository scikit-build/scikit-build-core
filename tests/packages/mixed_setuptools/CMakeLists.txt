cmake_minimum_required(VERSION 3.15...3.26)
project("${SKBUILD_PROJECT_NAME}" LANGUAGES C)

if(NOT EXAMPLE_DEFINE1 EQUAL 1)
  message(FATAL_ERROR "Example define 1 is not set")
endif()

if(NOT EXAMPLE_DEFINE2 EQUAL 2)
  message(FATAL_ERROR "Example define 2 is not set")
endif()

if(NOT EXAMPLE_DEFINE3 EQUAL 3)
  message(FATAL_ERROR "Example define 3 is not set")
endif()

if(NOT EXAMPLE_DEFINE4 EQUAL 4)
  message(FATAL_ERROR "Example define 4 is not set")
endif()

if(NOT EXAMPLE_DEFINE5 EQUAL 5)
  message(FATAL_ERROR "Example define 5 is not set")
endif()

find_package(
  Python
  COMPONENTS Interpreter Development.Module
  REQUIRED)
python_add_library(_core MODULE src/main.c WITH_SOABI)

install(TARGETS _core LIBRARY DESTINATION mixed_setuptools)
