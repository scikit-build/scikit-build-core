cmake_minimum_required(VERSION 3.15)
project(dummy LANGUAGES NONE)

include("${CMAKE_CURRENT_SOURCE_DIR}/tools/dummy_helper.cmake")

add_library(dummy_lib INTERFACE)
target_include_directories(dummy_lib
                           INTERFACE "${CMAKE_CURRENT_SOURCE_DIR}/include")
