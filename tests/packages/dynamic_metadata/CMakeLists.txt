cmake_minimum_required(VERSION 3.15...4.3)

project(
  ${SKBUILD_PROJECT_NAME}
  LANGUAGES C
  VERSION ${SKBUILD_PROJECT_VERSION})

find_package(Python COMPONENTS Interpreter Development.Module)
set(Python_SOABI ${SKBUILD_SOABI})

python_add_library(_module MODULE src/module.c WITH_SOABI)

install(TARGETS _module DESTINATION ${SKBUILD_PROJECT_NAME})
install(
  CODE "execute_process(COMMAND ${Python_EXECUTABLE} -V COMMAND_ECHO STDOUT)")
