cmake_minimum_required(VERSION 3.15...3.26)
project(
  "${SKBUILD_PROJECT_NAME}"
  LANGUAGES C
  VERSION "${SKBUILD_PROJECT_VERSION}")

file(TOUCH ${CMAKE_CURRENT_BINARY_DIR}/in_headers.h)
file(TOUCH ${CMAKE_CURRENT_BINARY_DIR}/in_scripts.py)
file(TOUCH ${CMAKE_CURRENT_BINARY_DIR}/in_data.txt)
file(TOUCH ${CMAKE_CURRENT_BINARY_DIR}/main.py)
file(TOUCH ${CMAKE_CURRENT_BINARY_DIR}/random_file.py)

install(FILES ${CMAKE_CURRENT_BINARY_DIR}/random_file.py
        DESTINATION ${SKBUILD_PLATLIB_DIR})
install(FILES ${CMAKE_CURRENT_BINARY_DIR}/in_headers.h
        DESTINATION ${SKBUILD_HEADERS_DIR})
install(FILES ${CMAKE_CURRENT_BINARY_DIR}/in_scripts.py
        DESTINATION ${SKBUILD_SCRIPTS_DIR})
install(FILES ${CMAKE_CURRENT_BINARY_DIR}/in_data.txt
        DESTINATION ${SKBUILD_DATA_DIR})
install(FILES ${CMAKE_CURRENT_BINARY_DIR}/main.py DESTINATION .)

if(NOT "${SOME_DEFINE}" STREQUAL "foo")
  message(FATAL_ERROR "SOME_DEFINE should be foo, is '${SOME_DEFINE}'")
endif()

if(NOT "${SOME_DEFINE2}" STREQUAL "bar")
  message(FATAL_ERROR "SOME_DEFINE2 should be bar, is '${SOME_DEFINE2}'")
endif()

if(NOT "${SOME_DEFINE3}" STREQUAL "baz")
  message(FATAL_ERROR "SOME_DEFINE3 should be baz, is '${SOME_DEFINE3}'")
endif()

if(NOT "${SOME_DEFINE4}" STREQUAL "baz")
  message(FATAL_ERROR "SOME_DEFINE3 should be baz, is '${SOME_DEFINE3}'")
endif()

if(NOT "${SOME_ARGS1}" STREQUAL "baz")
  message(FATAL_ERROR "SOME_ARGS1 should be baz, is '${SOME_ARGS1}'")
endif()

if(DEFINED "${SOME_ARGS2}")
  message(FATAL_ERROR "args should not be combined, last one wins")
endif()
