cmake_minimum_required(VERSION 3.15...4.4)
project(
  "${SKBUILD_PROJECT_NAME}"
  LANGUAGES NONE
  VERSION "${SKBUILD_PROJECT_VERSION}")

file(WRITE "${CMAKE_CURRENT_BINARY_DIR}/staged_install_example.h"
     "#define STAGED_ANSWER 42\n")
install(FILES "${CMAKE_CURRENT_BINARY_DIR}/staged_install_example.h"
        DESTINATION include)
