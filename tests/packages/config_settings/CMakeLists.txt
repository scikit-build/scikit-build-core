cmake_minimum_required(VERSION 3.15...4.3)
project(config_settings LANGUAGES NONE)

set(ZMQ_PREFIX
    ""
    CACHE STRING "")
set(ZMQ_LIBZMQ
    ""
    CACHE STRING "")

set(out_file "${CMAKE_CURRENT_BINARY_DIR}/log.txt")
file(WRITE "${out_file}" "ZMQ_PREFIX = ${ZMQ_PREFIX}\n")
file(APPEND "${out_file}" "ZMQ_LIBZMQ = ${ZMQ_LIBZMQ}\n")
