from __future__ import annotations

from scikit_build_core.settings.auto_cmake_version import find_min_cmake_version


def test_find_cmake_version_found():
    result = find_min_cmake_version("cmake_minimum_required(VERSION 3.15)")
    assert result == "3.15"


def test_find_cmake_version_with_fatal_error():
    result = find_min_cmake_version("cmake_minimum_required(VERSION 3.15 FATAL_ERROR)")
    assert result == "3.15"


def test_find_cmake_version_with_quotes():
    result = find_min_cmake_version('cmake_minimum_required("3.20")')
    assert result == "3.20"


def test_find_cmake_version_not_found():
    result = find_min_cmake_version("project(foo)")
    assert result is None
