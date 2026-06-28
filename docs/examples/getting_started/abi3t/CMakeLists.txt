cmake_minimum_required(VERSION 3.15...4.4)
project(${SKBUILD_PROJECT_NAME} LANGUAGES C)

find_package(
  Python
  COMPONENTS Interpreter Development.SABIModule
  REQUIRED)

# Use the Stable ABI version and SOABI suffix scikit-build-core resolved
# (3.15 / abi3t for a free-threaded build, or abi3 for a GIL build).
if(SKBUILD_SOABI)
  set(Python_SOABI ${SKBUILD_SOABI})
endif()

python_add_library(example MODULE example.c WITH_SOABI USE_SABI
                   ${SKBUILD_SABI_VERSION})

# CMake < 4.4 has no abi3t awareness, so pass the target define ourselves.
# scikit-build-core requests abi3t via this cache variable.
if(Py_TARGET_ABI3T)
  target_compile_definitions(example PRIVATE Py_TARGET_ABI3T=0x030f0000)
endif()

install(TARGETS example DESTINATION .)
