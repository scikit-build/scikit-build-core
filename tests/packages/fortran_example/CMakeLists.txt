cmake_minimum_required(VERSION 3.17.2...3.29)

project(
  fibby
  VERSION 1.0
  DESCRIPTION "FIB module"
  LANGUAGES C Fortran)

find_package(Python REQUIRED COMPONENTS Interpreter Development.Module NumPy)

# Grab the variables from a local Python installation F2PY headers
execute_process(
  COMMAND "${Python_EXECUTABLE}" -c
          "import numpy.f2py; print(numpy.f2py.get_include())"
  OUTPUT_VARIABLE F2PY_INCLUDE_DIR
  OUTPUT_STRIP_TRAILING_WHITESPACE)

# Generate the wrapper files
add_custom_command(
  OUTPUT fibbymodule.c fibby-f2pywrappers.f
  COMMAND Python::Interpreter -m numpy.f2py --lower
          "${CMAKE_CURRENT_SOURCE_DIR}/fib1.f" -m fibby
  COMMAND cmake -E touch fibby-f2pywrappers.f
  VERBATIM
  DEPENDS fib1.f)

python_add_library(
  fibby
  MODULE
  WITH_SOABI
  "${CMAKE_CURRENT_BINARY_DIR}/fibbymodule.c"
  "${CMAKE_CURRENT_BINARY_DIR}/fibby-f2pywrappers.f"
  "${F2PY_INCLUDE_DIR}/fortranobject.c"
  fib1.f)

target_include_directories(fibby PUBLIC ${F2PY_INCLUDE_DIR})
target_link_libraries(fibby PUBLIC Python::NumPy)

install(TARGETS fibby DESTINATION .)
