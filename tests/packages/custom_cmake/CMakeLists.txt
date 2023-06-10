cmake_minimum_required(VERSION 3.15...3.26)

project(
  ${SKBUILD_PROJECT_NAME}
  LANGUAGES
  VERSION ${SKBUILD_PROJECT_VERSION})

find_package(ExamplePkg REQUIRED)

include(ExampleInclude)

if(NOT EXAMPLE_INCLUDE_FOUND)
  message(FATAL_ERROR "ExampleInclude not found")
endif()

# Testing scripts
install(PROGRAMS scripts/script1 DESTINATION "${SKBUILD_SCRIPTS_DIR}")
