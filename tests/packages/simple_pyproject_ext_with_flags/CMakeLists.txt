cmake_minimum_required(VERSION 3.15...3.26)
project(
  "${SKBUILD_PROJECT_NAME}"
  LANGUAGES CXX
  VERSION "${SKBUILD_PROJECT_VERSION}")

add_library(cmake_example src/main.cpp)
install(TARGETS cmake_example LIBRARY DESTINATION .)
