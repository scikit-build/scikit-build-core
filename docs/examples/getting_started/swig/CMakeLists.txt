cmake_minimum_required(VERSION 3.15...3.26)
project(${SKBUILD_PROJECT_NAME} LANGUAGES C)

find_package(
  Python
  COMPONENTS Interpreter Development.Module
  REQUIRED)

find_package(
  SWIG
  COMPONENTS python
  REQUIRED)

add_custom_command(
  OUTPUT example.py example_wrap.c
  COMMAND ${SWIG_EXECUTABLE} -python -outcurrentdir
          "${CMAKE_CURRENT_SOURCE_DIR}/example.i"
  DEPENDS example.i)

python_add_library(_example MODULE example.c
                   "${CMAKE_CURRENT_BINARY_DIR}/example_wrap.c" WITH_SOABI)

install(TARGETS _example DESTINATION .)
install(FILES "${CMAKE_CURRENT_BINARY_DIR}/example.py" DESTINATION .)
