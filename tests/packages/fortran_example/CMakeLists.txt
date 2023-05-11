# setup project ###
cmake_minimum_required(VERSION 3.17.2...3.24)

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

# Prepping the module
set(f2py_module_name "fibby")
set(fortran_src_file "${CMAKE_CURRENT_SOURCE_DIR}/fib1.f")
set(f2py_module_c "${f2py_module_name}module.c")

# Target for enforcing dependencies
add_custom_target(genpyf DEPENDS "${fortran_src_file}")
add_custom_command(
  OUTPUT "${CMAKE_CURRENT_BINARY_DIR}/${f2py_module_c}"
  COMMAND ${Python_EXECUTABLE} -m "numpy.f2py" "${fortran_src_file}" -m "fibby"
          --lower # Important
  DEPENDS fib1.f # Fortran source
)

python_add_library(
  ${CMAKE_PROJECT_NAME} MODULE WITH_SOABI "${f2py_module_name}module.c"
  "${F2PY_INCLUDE_DIR}/fortranobject.c" "${fortran_src_file}")

target_include_directories(${CMAKE_PROJECT_NAME} PUBLIC ${F2PY_INCLUDE_DIR})
target_link_libraries(${CMAKE_PROJECT_NAME} PUBLIC Python::NumPy)

add_dependencies(${CMAKE_PROJECT_NAME} genpyf)

install(TARGETS ${CMAKE_PROJECT_NAME} DESTINATION .)
