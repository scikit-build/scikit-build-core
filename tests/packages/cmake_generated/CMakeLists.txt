cmake_minimum_required(VERSION 3.15)

project(
  ${SKBUILD_PROJECT_NAME}
  LANGUAGES CXX
  VERSION 1.2.3)

# Generate files at config time (configure_file) and at build time (add_custom_command)
# Note that bundling a generated file with sdist is out of scope for now.
# Note: cmake_generated/nested1/generated.py should try to open both generated and static files.
configure_file(src/cmake_generated/nested1/generated.py.in generated.py)
# We always expect the install phase to run, so the build tree layout can be
# different than the package layout.
install(FILES ${CMAKE_CURRENT_BINARY_DIR}/generated.py DESTINATION ${SKBUILD_PROJECT_NAME}/nested1)

file(GENERATE
    OUTPUT configured_file
    CONTENT "value written by cmake file generation")
install(FILES ${CMAKE_CURRENT_BINARY_DIR}/configured_file DESTINATION ${SKBUILD_PROJECT_NAME})

set(OUTPUT_FILE "${CMAKE_CURRENT_BINARY_DIR}/generated_data")
set(FILE_CONTENT "value written by cmake custom_command")
set(GENERATE_SCRIPT
  "file(WRITE \"${OUTPUT_FILE}\" \"${FILE_CONTENT}\")"
)
add_custom_command(
  OUTPUT "${OUTPUT_FILE}"
  COMMAND "${CMAKE_COMMAND}"
          -P "${CMAKE_CURRENT_BINARY_DIR}/generate_file.cmake"
  DEPENDS "${CMAKE_CURRENT_BINARY_DIR}/generate_file.cmake"
  COMMENT "Generating ${OUTPUT_FILE} using CMake scripting at build time"
  VERBATIM
)
file(WRITE "${CMAKE_CURRENT_BINARY_DIR}/generate_file.cmake" "${GENERATE_SCRIPT}")
add_custom_target(generate_file ALL
  DEPENDS "${OUTPUT_FILE}"
)
install(FILES "${OUTPUT_FILE}" DESTINATION ${SKBUILD_PROJECT_NAME}/namespace1)

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
