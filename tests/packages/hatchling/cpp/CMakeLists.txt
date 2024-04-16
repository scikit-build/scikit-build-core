cmake_minimum_required(VERSION 3.15...3.29)
project(extensionlib_example_cmake LANGUAGES CXX)

set(PYBIND11_FINDPYTHON ON)
find_package(pybind11 CONFIG REQUIRED)

pybind11_add_module(_core MODULE example.cpp)
install(TARGETS _core DESTINATION .)

if(NOT DEFINED SKBUILD_HATCHLING)
  message(
    FATAL_ERROR "This project should be built using scikit-build & hatchling")
endif()

# Testing metadata
file(WRITE "${CMAKE_CURRENT_BINARY_DIR}/metadata_file.txt" "Testing")
install(FILES "${CMAKE_CURRENT_BINARY_DIR}/metadata_file.txt"
        DESTINATION "${SKBUILD_METADATA_DIR}/extra_metadata/")

# Testing scripts
file(WRITE "${CMAKE_CURRENT_BINARY_DIR}/myscript"
     "#!/usr/bin/env python\nprint('Hello from myscript.py')")
install(FILES "${CMAKE_CURRENT_BINARY_DIR}/myscript"
        DESTINATION "${SKBUILD_SCRIPTS_DIR}")

# Testing data
file(WRITE "${CMAKE_CURRENT_BINARY_DIR}/data_file.txt" "Data")
install(FILES "${CMAKE_CURRENT_BINARY_DIR}/data_file.txt"
        DESTINATION "${SKBUILD_DATA_DIR}")
