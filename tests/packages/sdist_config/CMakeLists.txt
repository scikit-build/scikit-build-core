cmake_minimum_required(VERSION 3.15...4.4)
project(
  sdist_config
  LANGUAGES C
  VERSION ${SKBUILD_PROJECT_VERSION})

include(FetchContent)

# The "dependency" is a tiny project committed under external/dummy; it is
# "fetched" (copied) into the source tree so that sdist.cmake = true bundles it
# into the sdist, where the integrated copy is used instead of re-fetching.
if(NOT SKBUILD_STATE STREQUAL "sdist"
   AND EXISTS "${CMAKE_CURRENT_SOURCE_DIR}/dummy/CMakeLists.txt")
  message(STATUS "Using integrated dummy")
  add_subdirectory(dummy)
else()
  message(STATUS "Fetching dummy project")
  FetchContent_Declare(dummy URL "${CMAKE_CURRENT_SOURCE_DIR}/external/dummy"
                                 SOURCE_DIR ${CMAKE_CURRENT_SOURCE_DIR}/dummy)
  FetchContent_MakeAvailable(dummy)
endif()

find_package(
  Python
  COMPONENTS Interpreter Development.Module
  REQUIRED)
python_add_library(sdist_config MODULE main.c WITH_SOABI)
target_link_libraries(sdist_config PRIVATE dummy_lib)
install(TARGETS sdist_config DESTINATION .)

# Generation test
include("${CMAKE_CURRENT_BINARY_DIR}/output.cmake")
if(NOT "${MY_VERSION}" STREQUAL "${PROJECT_VERSION}")
  message(FATAL_ERROR "Version mismatch: ${MY_VERSION} != ${PROJECT_VERSION}")
endif()

include("${CMAKE_CURRENT_SOURCE_DIR}/overwrite.cmake")
if(NOT "${MY_NAME}" STREQUAL "${SKBUILD_PROJECT_NAME}")
  message(FATAL_ERROR "Name mismatch: ${MY_NAME} != ${SKBUILD_PROJECT_NAME}")
endif()
