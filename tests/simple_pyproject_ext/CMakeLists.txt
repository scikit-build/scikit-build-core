cmake_minimum_required(VERSION 3.15...3.24)
project("${SKBUILD_PROJECT_NAME}"
        LANGUAGES CXX
        VERSION "${SKBUILD_PROJECT_VERSION}")

execute_process(
COMMAND "${PYTHON_EXECUTABLE}" -c
        "import pybind11; print(pybind11.get_cmake_dir())"
OUTPUT_VARIABLE _tmp_dir
OUTPUT_STRIP_TRAILING_WHITESPACE COMMAND_ECHO STDOUT)
list(APPEND CMAKE_PREFIX_PATH "${_tmp_dir}")

find_package(Python COMPONENTS Interpreter Development.Module REQUIRED)

find_package(pybind11 CONFIG REQUIRED)
pybind11_add_module(cmake_example src/main.cpp)

target_compile_definitions(cmake_example
                           PRIVATE VERSION_INFO=${PROJECT_VERSION})
