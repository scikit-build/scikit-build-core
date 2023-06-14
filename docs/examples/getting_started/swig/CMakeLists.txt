cmake_minimum_required(VERSION 3.15...3.26)
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
  example
  LANGUAGE python OUTPUT_DIR "${SKBUILD_PLATLIB_DIR}"
  SOURCES example.i example.c)
if(WIN32)
  set_property(TARGET example PROPERTY SUFFIX ".${Python_SOABI}.pyd")
else()
  set_property(TARGET example
               PROPERTY SUFFIX ".${Python_SOABI}${CMAKE_SHARED_MODULE_SUFFIX}")
endif()
target_link_libraries(example PRIVATE Python::Module)

install(TARGETS example DESTINATION .)
