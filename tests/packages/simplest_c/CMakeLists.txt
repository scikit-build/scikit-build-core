cmake_minimum_required(VERSION 3.15...3.24)

project(${SKBUILD_PROJECT_NAME} LANGUAGES C VERSION ${SKBUILD_PROJECT_VERSION})

find_package(Python COMPONENTS COMPONENTS Interpreter Development.Module)

Python_add_library(_module MODULE src/module.c WITH_SOABI)

install(TARGETS _module DESTINATION ${SKBUILD_PROJECT_NAME})
install(FILES src/simplest/__init__.py
        DESTINATION ${SKBUILD_PROJECT_NAME})
