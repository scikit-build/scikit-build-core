cmake_minimum_required(VERSION 3.15...3.26)
project(${SKBUILD_PROJECT_NAME} LANGUAGES C)

add_library(example MODULE example.c)

install(TARGETS example DESTINATION example)
