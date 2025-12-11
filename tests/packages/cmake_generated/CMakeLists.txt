cmake_minimum_required(VERSION 3.15)

project(
  ${SKBUILD_PROJECT_NAME}
  LANGUAGES CXX
  VERSION 1.2.3)

add_library(pkg MODULE src/cmake_generated/pkg.cpp)

if(NOT WIN32)
    # Explicitly set the bundle extension to .so
    set_target_properties(pkg PROPERTIES
        SUFFIX ".so"
    )
endif()

# Set the library name to "pkg", regardless of the OS convention.
set_target_properties(pkg PROPERTIES PREFIX "")
install(TARGETS pkg DESTINATION ${SKBUILD_PROJECT_NAME})
