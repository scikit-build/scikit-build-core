cmake_minimum_required(VERSION 3.15...3.26)
project(${SKBUILD_PROJECT_NAME} LANGUAGES C Fortran)

find_package(
  Python
  COMPONENTS Interpreter Development.Module NumPy
  REQUIRED)

# F2PY headers
execute_process(
  COMMAND "${PYTHON_EXECUTABLE}" -c
          "import numpy.f2py; print(numpy.f2py.get_include())"
  OUTPUT_VARIABLE F2PY_INCLUDE_DIR
  OUTPUT_STRIP_TRAILING_WHITESPACE)

add_custom_command(
  OUTPUT examplemodule.c example-f2pywrappers.f
  DEPENDS example.f
  VERBATIM
  COMMAND "${Python_EXECUTABLE}" -m numpy.f2py
          "${CMAKE_CURRENT_SOURCE_DIR}/example.f" -m example --lower)

python_add_library(
  example MODULE "${CMAKE_CURRENT_BINARY_DIR}/examplemodule.c"
  "${F2PY_INCLUDE_DIR}/fortranobject.c" "${CMAKE_CURRENT_SOURCE_DIR}/example.f"
  WITH_SOABI)
target_link_libraries(example PRIVATE Python::NumPy)
target_include_directories(example PRIVATE "${F2PY_INCLUDE_DIR}")

install(TARGETS example DESTINATION .)
