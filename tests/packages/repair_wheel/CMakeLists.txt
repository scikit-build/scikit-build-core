cmake_minimum_required(VERSION 3.15...3.26)

project(${SKBUILD_PROJECT_NAME} LANGUAGES CXX)

include(GNUInstallDirs)
include(CMakePackageConfigHelpers)

find_package(Base CONFIG REQUIRED)
find_package(Python COMPONENTS Interpreter Development.Module)

add_executable(main src/main.cpp)
add_library(other SHARED src/other.cpp)
python_add_library(_module MODULE src/module.cpp WITH_SOABI)

target_link_libraries(other PRIVATE base::base)
target_link_libraries(main PRIVATE other)
target_link_libraries(_module PRIVATE base::base)

install(TARGETS main other)
install(TARGETS _module DESTINATION ".")
