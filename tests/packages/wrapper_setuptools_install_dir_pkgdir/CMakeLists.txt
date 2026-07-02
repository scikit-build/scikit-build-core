cmake_minimum_required(VERSION 3.15...4.3)
project(
  "${SKBUILD_PROJECT_NAME}"
  LANGUAGES C
  VERSION "${SKBUILD_PROJECT_VERSION}")

find_package(
  Python
  COMPONENTS Interpreter Development.Module
  REQUIRED)
python_add_library(_core MODULE src/main.c WITH_SOABI)

target_compile_definitions(_core PRIVATE VERSION_INFO=${PROJECT_VERSION})

install(TARGETS _core LIBRARY DESTINATION .)
