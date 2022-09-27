import dataclasses
from pathlib import Path
from typing import List

# from scikit_build_core.settings.convert import read_config_settings
from scikit_build_core.settings.sources import (
    ConfSource,
    EnvSource,
    SourceChain,
    TOMLSource,
)


@dataclasses.dataclass
class SettingChecker:
    zero: Path
    one: str
    two: int
    three: List[str]
    four: List[int]
    five: str = "empty"
    six: Path = Path("empty")


def test_env(monkeypatch):
    monkeypatch.setenv("SKBUILD_ZERO", "zero")
    monkeypatch.setenv("SKBUILD_ONE", "one")
    monkeypatch.setenv("SKBUILD_TWO", "2")
    monkeypatch.setenv("SKBUILD_THREE", "three")
    monkeypatch.setenv("SKBUILD_FOUR", "4")
    monkeypatch.setenv("SKBUILD_FIVE", "five")
    monkeypatch.setenv("SKBUILD_SIX", "six")

    sources = SourceChain(
        EnvSource("SKBUILD"),
        ConfSource(settings={}),
        TOMLSource(settings={}),
    )
    settings = sources.convert_target(SettingChecker)

    assert settings.zero == Path("zero")
    assert settings.one == "one"
    assert settings.two == 2
    assert settings.three == ["three"]
    assert settings.four == [4]
    assert settings.five == "five"
    assert settings.six == Path("six")


def test_conf():
    config_settings = {
        "zero": "zero",
        "one": "one",
        "two": "2",
        "three": ["three"],
        "four": ["4"],
        "five": "five",
        "six": "six",
    }

    sources = SourceChain(
        EnvSource("SKBUILD"),
        ConfSource(settings=config_settings),
        TOMLSource(settings={}),
    )
    settings = sources.convert_target(SettingChecker)

    assert settings.zero == Path("zero")
    assert settings.one == "one"
    assert settings.two == 2
    assert settings.three == ["three"]
    assert settings.four == [4]
    assert settings.five == "five"
    assert settings.six == Path("six")


def test_toml():
    toml_settings = {
        "zero": "zero",
        "one": "one",
        "two": 2,
        "three": ["three"],
        "four": [4],
        "five": "five",
        "six": "six",
    }

    sources = SourceChain(
        EnvSource("SKBUILD"),
        ConfSource(settings={}),
        TOMLSource(settings=toml_settings),
    )
    settings = sources.convert_target(SettingChecker)

    assert settings.zero == Path("zero")
    assert settings.one == "one"
    assert settings.two == 2
    assert settings.three == ["three"]
    assert settings.four == [4]
    assert settings.five == "five"
    assert settings.six == Path("six")


@dataclasses.dataclass
class NestedSettingChecker:
    zero: Path
    one: str
    two: SettingChecker
    three: int = 3


def test_env_nested(monkeypatch):
    monkeypatch.setenv("SKBUILD_ZERO", "zero")
    monkeypatch.setenv("SKBUILD_ONE", "one")
    monkeypatch.setenv("SKBUILD_TWO_ZERO", "zero")
    monkeypatch.setenv("SKBUILD_TWO_ONE", "one")
    monkeypatch.setenv("SKBUILD_TWO_TWO", "2")
    monkeypatch.setenv("SKBUILD_TWO_THREE", "three")
    monkeypatch.setenv("SKBUILD_TWO_FOUR", "4")

    sources = SourceChain(
        EnvSource("SKBUILD"),
        ConfSource(settings={}),
        TOMLSource(settings={}),
    )
    settings = sources.convert_target(NestedSettingChecker)

    assert settings.zero == Path("zero")
    assert settings.one == "one"
    assert settings.two.zero == Path("zero")
    assert settings.two.one == "one"
    assert settings.two.two == 2
    assert settings.two.three == ["three"]
    assert settings.two.four == [4]
    assert settings.two.five == "empty"
    assert settings.two.six == Path("empty")
    assert settings.three == 3


def test_conf_nested():
    config_settings = {
        "zero": "zero",
        "one": "one",
        "two.zero": "zero",
        "two.one": "one",
        "two.two": "2",
        "two.three": ["three"],
        "two.four": ["4"],
    }

    sources = SourceChain(
        EnvSource("SKBUILD"),
        ConfSource(settings=config_settings),
        TOMLSource(settings={}),
    )
    settings = sources.convert_target(NestedSettingChecker)

    assert settings.zero == Path("zero")
    assert settings.one == "one"
    assert settings.two.zero == Path("zero")
    assert settings.two.one == "one"
    assert settings.two.two == 2
    assert settings.two.three == ["three"]
    assert settings.two.four == [4]
    assert settings.two.five == "empty"
    assert settings.two.six == Path("empty")
    assert settings.three == 3


def test_toml_nested():
    toml_settings = {
        "zero": "zero",
        "one": "one",
        "two": {
            "zero": "zero",
            "one": "one",
            "two": 2,
            "three": ["three"],
            "four": [4],
        },
    }

    sources = SourceChain(
        EnvSource("SKBUILD"),
        ConfSource(settings={}),
        TOMLSource(settings=toml_settings),
    )
    settings = sources.convert_target(NestedSettingChecker)

    assert settings.zero == Path("zero")
    assert settings.one == "one"
    assert settings.two.zero == Path("zero")
    assert settings.two.one == "one"
    assert settings.two.two == 2
    assert settings.two.three == ["three"]
    assert settings.two.four == [4]
    assert settings.two.five == "empty"
    assert settings.two.six == Path("empty")
    assert settings.three == 3
