cmake_minimum_required(VERSION 3.15...3.26)

project(simple_pure LANGUAGES CXX)

add_executable(simple_pure simple_pure.cpp)

target_compile_features(simple_pure PUBLIC cxx_std_11)

install(TARGETS simple_pure)

if(DEFINED SKBUILD)
  message(STATUS "SKBUILD is defined to ${SKBUILD}")
endif()

if(DEFINED SKBUILD2)
  message(STATUS "SKBUILD2 is defined to ${SKBUILD2}")
endif()
