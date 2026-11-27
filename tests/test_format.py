from __future__ import annotations

import pytest

from scikit_build_core.format import (
    RootPathResolver,
    format_template,
    pyproject_format,
    template_glob,
)
from scikit_build_core.settings.skbuild_model import ScikitBuildSettings

TYPE_CHECKING = False
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


def test_name_key_omitted_by_default() -> None:
    settings = ScikitBuildSettings()
    assert "name" not in pyproject_format(settings=settings)


def test_name_key_present_when_given() -> None:
    settings = ScikitBuildSettings()
    formatted = pyproject_format(settings=settings, name="my_pkg")
    assert formatted["name"] == "my_pkg"
    assert "build/{name}".format(**formatted) == "build/my_pkg"


@pytest.mark.parametrize(
    ("template", "expected"),
    [
        ("{wheel_tag}", "*"),
        ("{root}", "*"),
        ("{root:uri}", "*"),
        ("{root:parent:uri}", "*"),
        ("build/{root:uri}/x", "build/*/x"),
        ("{build_dir}/install", "*/install"),
        ("out/{state!r}", "out/'*'"),
        ("out/{state!a}/x", "out/'*'/x"),
        ("out/{state!s}", "out/*"),
        ("out/{state!r:>9}", "out/*"),
    ],
)
def test_template_glob(template: str, expected: str) -> None:
    assert template_glob(template, key="build-dir") == expected


def test_rebuild_dir_follows_build_dir(tmp_path: Path) -> None:
    from scikit_build_core.build.common_wheel_helpers import get_editable_rebuild_dir
    from scikit_build_core.builder.wheel_tag import WheelTag

    settings = ScikitBuildSettings()
    settings.editable.rebuild_dir = "{build_dir}/install/{wheel_tag}"
    tags = WheelTag(pyvers=["py3"], abis=["none"], archs=["any"])
    result = get_editable_rebuild_dir(
        settings,
        build_dir=tmp_path / "build",
        targetlib="platlib",
        tags=tags,
        state="editable",
        name="pkg",
    )
    assert result == (tmp_path / "build" / "install" / "py3-none-any").resolve()


def test_format_template() -> None:
    assert format_template("a-{x}", {"x": "b"}, key="build-dir") == "a-b"


@pytest.mark.parametrize(
    ("template", "match"),
    [
        ("{nope}", "unknown placeholder 'nope'"),
        ("{unclosed", "expected '}'"),
        ("{x.nope}", "attribute"),
        ("{}", "index"),
    ],
)
def test_format_template_errors(
    capsys: pytest.CaptureFixture[str], template: str, match: str
) -> None:
    with pytest.raises(SystemExit):
        format_template(template, {"x": "b"}, key="build-dir")
    err = capsys.readouterr().err
    assert "build-dir: " in err
    assert match in err
