from __future__ import annotations

import warnings
from unittest.mock import patch

import pytest

from scikit_build_core.setuptools.wrapper import setup


def test_wrapper_basic():
    with patch("setuptools.setup") as mock_setup:
        setup(cmake_source_dir=".")
    mock_setup.assert_called_once_with(
        cmake_source_dir=".", cmake_args=(), distclass=pytest.importorskip("setuptools").Distribution
    )


def test_wrapper_unsupported_cmake_install_dir():
    with pytest.raises(AssertionError, match="cmake_install_dir not supported"):
        setup(cmake_install_dir="build")


def test_wrapper_unsupported_cmake_with_sdist():
    with pytest.raises(AssertionError, match="cmake_with_sdist not supported"):
        setup(cmake_with_sdist=True)


def test_wrapper_unsupported_manifest_hook():
    with pytest.raises(AssertionError, match="cmake_process_manifest_hook not supported"):
        setup(cmake_process_manifest_hook=lambda f: f)


def test_wrapper_unsupported_install_target():
    with pytest.raises(AssertionError, match="cmake_install_target not supported"):
        setup(cmake_install_target="all")


def test_wrapper_deprecated_cmake_languages():
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        with patch("setuptools.setup"):
            setup(cmake_languages=["C++"])
    assert len(w) == 1
    assert "cmake_languages no longer has any effect" in str(w[0].message)


def test_wrapper_deprecated_cmake_minimum_version():
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        with patch("setuptools.setup"):
            setup(cmake_minimum_required_version="3.15")
    assert len(w) == 1
    assert "Set via pyproject.toml" in str(w[0].message)
