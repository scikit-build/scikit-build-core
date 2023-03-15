cmake_minimum_required(VERSION 3.15...3.26)

project(
  ${SKBUILD_PROJECT_NAME}
  LANGUAGES C
  VERSION ${SKBUILD_PROJECT_VERSION})

find_package(Python COMPONENTS Interpreter Development.Module)

python_add_library(_module MODULE src/module.c WITH_SOABI)

install(TARGETS _module DESTINATION ${SKBUILD_PROJECT_NAME})

# Testing artifacts
file(WRITE ${CMAKE_CURRENT_BINARY_DIR}/generated.txt "Testing")
install(FILES ${CMAKE_CURRENT_BINARY_DIR}/generated.txt
        DESTINATION ${SKBUILD_PROJECT_NAME})

file(WRITE ${CMAKE_CURRENT_BINARY_DIR}/generated_ignored.txt "Testing")
install(FILES ${CMAKE_CURRENT_BINARY_DIR}/generated_ignored.txt
        DESTINATION ${SKBUILD_PROJECT_NAME})
