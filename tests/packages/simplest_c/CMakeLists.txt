cmake_minimum_required(VERSION 3.15...3.26)

project(
  ${SKBUILD_PROJECT_NAME}
  LANGUAGES C
  VERSION ${SKBUILD_PROJECT_VERSION})

find_package(Python COMPONENTS Interpreter Development.Module)

python_add_library(_module MODULE src/module.c WITH_SOABI)

install(
  TARGETS _module
  DESTINATION ${SKBUILD_PROJECT_NAME}
  COMPONENT PythonModule)

if("${CMAKE_CURRENT_SOURCE_DIR}" STREQUAL "${CMAKE_CURRENT_BINARY_DIR}"
   AND DEFINED SKBUILD)
  # Editable in-place builds. THe empty generator expression ensures
  # multi-config enerators keeps us from having to set
  # LIBRARY_OUTPUT_DIRECTORY_<CONFIG> too.
  set_target_properties(
    _module PROPERTIES LIBRARY_OUTPUT_DIRECTORY
                       "${CMAKE_BINARY_DIR}/src/${SKBUILD_PROJECT_NAME}$<0:>")
endif()

# Testing artifacts
file(WRITE ${CMAKE_CURRENT_BINARY_DIR}/generated.txt "Testing")
install(
  FILES ${CMAKE_CURRENT_BINARY_DIR}/generated.txt
  DESTINATION ${SKBUILD_PROJECT_NAME}
  COMPONENT Generated)

file(WRITE ${CMAKE_CURRENT_BINARY_DIR}/generated_ignored.txt "Testing")
install(FILES ${CMAKE_CURRENT_BINARY_DIR}/generated_ignored.txt
        DESTINATION ${SKBUILD_PROJECT_NAME})

file(WRITE ${CMAKE_CURRENT_BINARY_DIR}/generated_no_wheel.txt "Testing")
install(FILES ${CMAKE_CURRENT_BINARY_DIR}/generated_no_wheel.txt
        DESTINATION ${SKBUILD_PROJECT_NAME})

# Testing metadata
file(WRITE ${CMAKE_CURRENT_BINARY_DIR}/metadata_file.txt "Testing")
file(WRITE ${CMAKE_CURRENT_BINARY_DIR}/LICENSE.txt "Testing")
install(FILES ${CMAKE_CURRENT_BINARY_DIR}/metadata_file.txt
        DESTINATION "${SKBUILD_METADATA_DIR}")
install(FILES ${CMAKE_CURRENT_BINARY_DIR}/LICENSE.txt
        DESTINATION "${SKBUILD_METADATA_DIR}/licenses")
