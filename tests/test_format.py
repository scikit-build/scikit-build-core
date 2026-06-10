from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from scikit_build_core.format import RootPathResolver, pyproject_format

if TYPE_CHECKING:
    from pathlib import Path


@pytest.fixture
def resolver(tmp_path: Path) -> RootPathResolver:
    return RootPathResolver(tmp_path)


def test_root_plain_format(resolver: RootPathResolver) -> None:
    # Regression: a bare {root} used to fall through to repr() and emit
    # "RootPathResolver(path=...)" instead of the path itself.
    formatted = f"{resolver}"
    assert formatted == str(resolver.path)
    assert "RootPathResolver" not in formatted


def test_root_str(resolver: RootPathResolver) -> None:
    assert str(resolver) == str(resolver.path)


def test_root_parent_format(resolver: RootPathResolver) -> None:
    # Regression: a terminal {root:parent} used to emit the repr.
    formatted = f"{resolver:parent}"
    assert formatted == str(resolver.path.parent)
    assert "RootPathResolver" not in formatted


def test_root_uri_format(resolver: RootPathResolver) -> None:
    assert f"{resolver:uri}" == resolver.path.as_uri()


def test_root_parent_uri_format(resolver: RootPathResolver) -> None:
    assert f"{resolver:parent:uri}" == resolver.path.parent.as_uri()


def test_root_invalid_format(resolver: RootPathResolver) -> None:
    with pytest.raises(ValueError, match="Could not handle format"):
        f"{resolver:nonsense}"


def test_dummy_plain_keys() -> None:
    dummy = pyproject_format(dummy=True)
    # All known keys are present and produce "*" for a plain format.
    assert dummy["wheel_tag"] == "*"
    assert "{wheel_tag}".format(**dummy) == "*"


@pytest.mark.parametrize(
    ("spec", "expected"),
    [
        ("{root}", "*"),
        ("{root:uri}", "*"),
        ("{root:parent:uri}", "*"),
        ("build/{root:uri}/x", "build/*/x"),
    ],
)
def test_dummy_root_spec(spec: str, expected: str) -> None:
    # Regression: dummy mode mapped root to the plain string "*", so any
    # build-dir containing a spec like {root:uri} raised
    # "ValueError: Invalid format specifier 'uri' for object of type 'str'".
    # The spec is kept out of a literal .format() call so linters don't try to
    # validate the custom :uri spec against a plain str.
    dummy = pyproject_format(dummy=True)
    assert spec.format(**dummy) == expected
