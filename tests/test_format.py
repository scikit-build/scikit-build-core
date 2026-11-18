from __future__ import annotations

import copy

import pytest

from scikit_build_core.format import (
    RootPathResolver,
    build_dir_exclude_patterns,
    config_setting_fields,
    pyproject_format,
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


def test_dummy_plain_keys() -> None:
    dummy = pyproject_format(dummy=True)
    # All known keys are present and produce "*" for a plain format.
    assert dummy["wheel_tag"] == "*"
    assert "{wheel_tag}".format(**dummy) == "*"
    assert dummy["name"] == "*"
    assert "{name}".format(**dummy) == "*"


def test_name_key_omitted_by_default() -> None:
    settings = ScikitBuildSettings()
    assert "name" not in pyproject_format(settings=settings)


def test_name_key_present_when_given() -> None:
    settings = ScikitBuildSettings()
    formatted = pyproject_format(settings=settings, name="my_pkg")
    assert formatted["name"] == "my_pkg"
    assert "build/{name}".format(**formatted) == "build/my_pkg"


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


def test_dummy_build_dir_key() -> None:
    assert "{build_dir}/install".format(**pyproject_format(dummy=True)) == "*/install"


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


def test_config_setting_key() -> None:
    formatted = pyproject_format(
        settings=ScikitBuildSettings(),
        config_settings={"torch.variant": "cu126", "my-proj.gpu-opt.x": True},
    )
    # Kept out of a literal .format() call; mypy rejects dotted index keys.
    spec = "build/{config_setting[torch.variant]}"
    assert spec.format(**formatted) == "build/cu126"
    spec = "{config_setting[my-proj.gpu-opt.x]}"
    assert spec.format(**formatted) == "true"


@pytest.mark.parametrize(
    ("spec", "match"),
    [
        ("{config_setting[torch.other]}", "not declared"),
        ("{config_setting[other.variant]}", "not declared"),
        ("{config_setting[torch]}", "not declared"),
        ("{config_setting[torch.unset]}", "unset"),
    ],
)
def test_config_setting_key_errors(spec: str, match: str) -> None:
    formatted = pyproject_format(
        settings=ScikitBuildSettings(),
        config_settings={"torch.variant": "cpu", "torch.unset": None},
    )
    with pytest.raises(ValueError, match=match):
        spec.format(**formatted)


def test_dummy_config_setting() -> None:
    dummy = pyproject_format(dummy=True)
    spec = "build/{config_setting[a.b-c]}"
    assert spec.format(**dummy) == "build/*"


def test_config_setting_name_is_prefix_of_another() -> None:
    formatted = pyproject_format(
        settings=ScikitBuildSettings(),
        config_settings={"pkg.opt": None, "pkg.opt.mode": "fast"},
    )
    spec = "{config_setting[pkg.opt.mode]}"
    assert spec.format(**formatted) == "fast"
    spec = "{config_setting[pkg.opt]}"
    with pytest.raises(ValueError, match="unset"):
        spec.format(**formatted)


@pytest.mark.parametrize("name", ["pkg._variant", "_pkg.x", "pkg.__class__"])
def test_config_setting_underscore_segments(name: str) -> None:
    formatted = pyproject_format(
        settings=ScikitBuildSettings(), config_settings={name: "value"}
    )
    spec = f"{{config_setting[{name}]}}"
    assert spec.format(**formatted) == "value"
    assert spec.format(**pyproject_format(dummy=True)) == "*"


@pytest.mark.parametrize("conversion", ["!s", "!r", "!a"])
def test_config_setting_conversion(conversion: str) -> None:
    formatted = pyproject_format(
        settings=ScikitBuildSettings(), config_settings={"pkg.variant": "cpu"}
    )
    full = f"{{config_setting[pkg.variant]{conversion}}}"
    assert full.format(**formatted) == ("cpu" if conversion == "!s" else "'cpu'")
    partial = f"{{config_setting[pkg]{conversion}}}"
    with pytest.raises(ValueError, match="not declared"):
        partial.format(**formatted)


@pytest.mark.parametrize(
    ("build_dir", "patterns"),
    [
        ("", []),
        ("build/{wheel_tag}", ["build/*"]),
        ("build/{config_setting[a.b]}", ["build/*", "build/*/**/*"]),
        # No literal text: the pattern would match every file.
        ("{config_setting[a.b]}", []),
        ("{wheel_tag}", []),
        # Adjacent placeholders must not make a ``**`` glob.
        ("src/{config_setting[a.b]}{config_setting[a.c]}", ["src/*", "src/*/**/*"]),
        ("src/{wheel_tag}{config_setting[a.b]}", ["src/*", "src/*/**/*"]),
        ("src/{wheel_tag}{name}", ["src/*"]),
    ],
)
def test_build_dir_exclude_patterns(build_dir: str, patterns: list[str]) -> None:
    assert list(build_dir_exclude_patterns(build_dir)) == patterns


def test_config_setting_fields() -> None:
    template = "{root}/{config_setting[a.b-c]}/{wheel_tag}-{config_setting[d]!r:>4}"
    assert config_setting_fields(template) == ["a.b-c", "d"]
    assert config_setting_fields("{config_setting}") == []
    assert config_setting_fields("{unclosed") == []


def test_config_setting_introspection() -> None:
    formatted = pyproject_format(
        settings=ScikitBuildSettings(), config_settings={"pkg.variant": "cpu"}
    )
    assert "pkg.variant" in repr(formatted)
    copied = copy.deepcopy(formatted)
    spec = "{config_setting[pkg.variant]}"
    assert spec.format(**copied) == "cpu"
