cmake_minimum_required(VERSION 3.15...4.3)
project(${SKBUILD_PROJECT_NAME} LANGUAGES C)

find_package(
  Python
  COMPONENTS Interpreter Development.Module
  REQUIRED)

find_package(
  SWIG
  COMPONENTS python
  REQUIRED)

include(UseSWIG)

swig_add_library(
  _core
  LANGUAGE python OUTPUT_DIR "${SKBUILD_PLATLIB_DIR}/${SKBUILD_PROJECT_NAME}"
  SOURCES src/${SKBUILD_PROJECT_NAME}/_core.i
          src/${SKBUILD_PROJECT_NAME}/_core.c)
if(WIN32)
  set_property(TARGET _core PROPERTY SUFFIX ".${Python_SOABI}.pyd")
else()
  set_property(TARGET _core
               PROPERTY SUFFIX ".${Python_SOABI}${CMAKE_SHARED_MODULE_SUFFIX}")
endif()
target_link_libraries(_core PRIVATE Python::Module)

install(TARGETS _core DESTINATION ${SKBUILD_PROJECT_NAME})
