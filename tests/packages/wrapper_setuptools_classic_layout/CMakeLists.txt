cmake_minimum_required(VERSION 3.15...3.26)
project(
  "${SKBUILD_PROJECT_NAME}"
  LANGUAGES CXX
  VERSION "${SKBUILD_PROJECT_VERSION}")

find_package(pybind11 CONFIG REQUIRED)
pybind11_add_module(_core src/main.cpp)

target_compile_definitions(_core PRIVATE VERSION_INFO=${PROJECT_VERSION})

install(TARGETS _core LIBRARY DESTINATION python/classic_layout_example)
install(FILES data/example.h DESTINATION include/classic_layout_example)
