cmake_minimum_required(VERSION 3.15...3.26)

project(Base LANGUAGES CXX)

include(GNUInstallDirs)
include(CMakePackageConfigHelpers)

set(CMAKE_WINDOWS_EXPORT_ALL_SYMBOLS ON)

add_library(base SHARED)

target_sources(base PRIVATE base.cpp)
set_property(
  TARGET base
  APPEND
  PROPERTY PUBLIC_HEADER base.h)
target_include_directories(
  base PUBLIC $<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}>
              $<INSTALL_INTERFACE:${CMAKE_INSTALL_INCLUDEDIR}>)

install(TARGETS base EXPORT BaseTargets)
install(
  EXPORT BaseTargets
  DESTINATION ${CMAKE_INSTALL_LIBDIR}/cmake/base
  NAMESPACE base::)
configure_package_config_file(
  BaseConfig.cmake.in BaseConfig.cmake
  INSTALL_DESTINATION ${CMAKE_INSTALL_LIBDIR}/cmake/Base)
install(FILES ${CMAKE_CURRENT_BINARY_DIR}/BaseConfig.cmake
        DESTINATION ${CMAKE_INSTALL_LIBDIR}/cmake/base)
