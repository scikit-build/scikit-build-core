cmake_minimum_required(VERSION 3.15...3.27)
project(sdist_config LANGUAGES CXX)

include(FetchContent)

if(NOT SKBUILD_STATE STREQUAL "sdist"
   AND EXISTS "${CMAKE_CURRENT_SOURCE_DIR}/pybind11/CMakeLists.txt")
  message(STATUS "Using integrated pybind11")
  set(FETCHCONTENT_FULLY_DISCONNECTED ON)
endif()

FetchContent_Declare(
  pybind11
  GIT_REPOSITORY https://github.com/pybind/pybind11.git
  GIT_TAG v2.11.1
  SOURCE_DIR ${CMAKE_CURRENT_SOURCE_DIR}/pybind11)

set(PYBIND11_FINDPYTHON ON)
FetchContent_MakeAvailable(pybind11)

pybind11_add_module(sdist_config main.cpp)
install(TARGETS sdist_config DESTINATION .)
