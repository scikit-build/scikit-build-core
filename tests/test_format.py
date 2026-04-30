from __future__ import annotations

from pathlib import Path

import pytest

from scikit_build_core.format import RootPathResolver, pyproject_format


class FakeSettings:
    class cmake:  # noqa: N801
        build_type = "Release"


def test_pyproject_format_basic():
    fmt = pyproject_format(settings=FakeSettings(), state="wheel")
    assert fmt["build_type"] == "Release"
    assert fmt["state"] == "wheel"
    assert "cache_tag" in fmt


def test_pyproject_format_dummy():
    fmt = pyproject_format(dummy=True)
    assert all(v == "*" for v in fmt.values())


def test_pyproject_format_with_tags():
    class FakeTag:
        def __str__(self):
            return "cp313-cp313-macosx_14_0_arm64"

    fmt = pyproject_format(settings=FakeSettings(), tags=FakeTag())
    assert fmt["wheel_tag"] == "cp313-cp313-macosx_14_0_arm64"


def test_root_path_resolver_uri():
    resolver = RootPathResolver()
    assert resolver.__format__("uri").startswith("file://")


def test_root_path_resolver_parent():
    resolver = RootPathResolver(Path("/a/b/c"))
    result = resolver.__format__("parent")
    assert "a/b" in result


def test_root_path_resolver_parent_uri():
    resolver = RootPathResolver(Path("/a/b/c"))
    result = resolver.__format__("parent:uri")
    assert result.endswith("/b")


def test_root_path_resolver_str():
    resolver = RootPathResolver(Path("/a/b"))
    result = resolver.__format__("")
    assert "RootPathResolver" in result or "/a/b" in result


def test_root_path_resolver_unknown():
    resolver = RootPathResolver()
    with pytest.raises(ValueError, match="Could not handle format"):
        resolver.__format__("unknown")
