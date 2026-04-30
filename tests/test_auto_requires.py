from __future__ import annotations

from packaging.version import Version

from scikit_build_core.settings.auto_requires import get_min_requires, min_from_spec


def test_min_from_spec_ge():
    from packaging.specifiers import Specifier

    assert min_from_spec(Specifier(">=3.15")) == Version("3.15")


def test_min_from_spec_eq():
    from packaging.specifiers import Specifier

    assert min_from_spec(Specifier("==3.15")) == Version("3.15")


def test_min_from_spec_tilde():
    from packaging.specifiers import Specifier

    assert min_from_spec(Specifier("~=3.15")) == Version("3.15")


def test_min_from_spec_gt():
    from packaging.specifiers import Specifier

    assert min_from_spec(Specifier(">3.15")) == Version("3.15")


def test_min_from_spec_no_min():
    from packaging.specifiers import Specifier

    assert min_from_spec(Specifier("<3.15")) is None


def test_get_min_requires_found():
    result = get_min_requires("cmake", ["cmake>=3.15", "ninja>=1.5"])
    assert result == Version("3.15")


def test_get_min_requires_not_found():
    result = get_min_requires("cmake", ["ninja>=1.5"])
    assert result is None


def test_get_min_requires_with_markers():
    result = get_min_requires(
        "cmake",
        ['cmake>=3.15; python_version >= "3.10"', 'cmake>=3.20; python_version < "3.10"'],
    )
    # At least one should match
    assert result is not None


def test_get_min_requires_multiple():
    result = get_min_requires("cmake", ["cmake>=3.15", "cmake>=3.20"])
    assert result == Version("3.15")
