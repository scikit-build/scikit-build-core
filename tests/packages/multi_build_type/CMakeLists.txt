cmake_minimum_required(VERSION 3.15...4.3)

project(
  ${SKBUILD_PROJECT_NAME}
  LANGUAGES NONE
  VERSION ${SKBUILD_PROJECT_VERSION})

# Install a marker file into a per-configuration directory. With
# cmake.build-type set to a list, this should produce one marker per build type,
# regardless of whether a single- or multi-config generator is used.
file(WRITE ${CMAKE_CURRENT_BINARY_DIR}/marker.txt "marker")
install(FILES ${CMAKE_CURRENT_BINARY_DIR}/marker.txt
        DESTINATION ${SKBUILD_PROJECT_NAME}/$<CONFIG>)
