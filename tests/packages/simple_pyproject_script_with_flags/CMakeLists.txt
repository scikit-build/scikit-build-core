cmake_minimum_required(VERSION 3.15...3.29)
project(
  "${SKBUILD_PROJECT_NAME}"
  LANGUAGES C
  VERSION "${SKBUILD_PROJECT_VERSION}")

add_executable(cmake_example src/main.c)
set_target_properties(cmake_example PROPERTIES POSITION_INDEPENDENT_CODE ON)
install(TARGETS cmake_example DESTINATION "${SKBUILD_SCRIPTS_DIR}")
