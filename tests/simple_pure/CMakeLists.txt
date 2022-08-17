cmake_minimum_required(VERSION 3.15...3.24)

project(simple_pure LANGUAGES CXX)

add_executable(simple_pure simple_pure.cpp)

target_compile_features(simple_pure PUBLIC cxx_std_17)

install(TARGETS simple_pure)
