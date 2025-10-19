cmake_minimum_required(VERSION 3.15...3.26)

project(${SKBUILD_PROJECT_NAME} LANGUAGES CXX)

set(CMAKE_WINDOWS_EXPORT_ALL_SYMBOLS ON)

include(GNUInstallDirs)
include(CMakePackageConfigHelpers)

find_package(Base CONFIG REQUIRED)
find_package(Python COMPONENTS Interpreter Development.Module)

add_executable(main src/main.cpp)
add_library(other SHARED src/other.cpp)
python_add_library(_module MODULE src/module.cpp WITH_SOABI)

target_link_libraries(other PRIVATE base::base)
target_link_libraries(main PRIVATE other)
target_link_libraries(_module PRIVATE base::base)

install(TARGETS main other)
install(TARGETS _module DESTINATION ".")

if(DO_MANUAL_REPAIR)
  if(APPLE)
    set(origin_token "@loader_path")
  else()
    set(origin_token "$ORIGIN")
  endif()
  set_property(
    TARGET main PROPERTY INSTALL_RPATH
                         "${origin_token}/../${CMAKE_INSTALL_LIBDIR}")
  set_property(
    TARGET other
    PROPERTY INSTALL_RPATH
             "${origin_token}/../../base_project/${CMAKE_INSTALL_LIBDIR}")
  set_property(
    TARGET _module
    PROPERTY INSTALL_RPATH
             "${origin_token}/../base_project/${CMAKE_INSTALL_LIBDIR}")
  if(WIN32)
    install(TARGETS other RUNTIME DESTINATION ${SKBUILD_SCRIPTS_DIR})
    file(
      WRITE ${CMAKE_CURRENT_BINARY_DIR}/__init__.py
      "
import os
import sysconfig
from pathlib import Path

base_project_bindir = Path(__file__).parent / \"../base_project/${CMAKE_INSTALL_BINDIR}\"
project_bindir = Path(__file__).parent / \"${CMAKE_INSTALL_BINDIR}\"
os.add_dll_directory(str(base_project_bindir))
os.add_dll_directory(str(project_bindir))
")
    install(FILES ${CMAKE_CURRENT_BINARY_DIR}/__init__.py DESTINATION ".")
  endif()
endif()
