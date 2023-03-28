import dataclasses
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

import pytest

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
    four: List[int] = dataclasses.field(default_factory=list)
    five: str = "empty"
    six: Path = Path("empty")
    seven: Union[int, None] = None
    eight: Dict[str, str] = dataclasses.field(default_factory=dict)
    nine: Dict[str, int] = dataclasses.field(default_factory=dict)
    # TOML only
    ten: Dict[str, Any] = dataclasses.field(default_factory=dict)


def test_empty(monkeypatch):
    monkeypatch.setenv("SKB_ZERO", "zero")
    monkeypatch.setenv("SKB_ONE", "one")
    monkeypatch.setenv("SKB_TWO", "2")
    monkeypatch.setenv("SKB_THREE", "three")

    sources = SourceChain(
        EnvSource("SKB"),
        ConfSource(settings={}),
        TOMLSource(settings={}),
    )
    settings = sources.convert_target(SettingChecker)

    assert settings.zero == Path("zero")
    assert settings.one == "one"
    assert settings.two == 2
    assert settings.three == ["three"]
    assert settings.four == []
    assert settings.five == "empty"
    assert settings.six == Path("empty")
    assert settings.seven is None
    assert settings.eight == {}
    assert settings.nine == {}


def test_env(monkeypatch):
    monkeypatch.setenv("SKBUILD_ZERO", "zero")
    monkeypatch.setenv("SKBUILD_ONE", "one")
    monkeypatch.setenv("SKBUILD_TWO", "2")
    monkeypatch.setenv("SKBUILD_THREE", "three")
    monkeypatch.setenv("SKBUILD_FOUR", "4")
    monkeypatch.setenv("SKBUILD_FIVE", "five")
    monkeypatch.setenv("SKBUILD_SIX", "six")
    monkeypatch.setenv("SKBUILD_SEVEN", "7")
    monkeypatch.setenv("SKBUILD_EIGHT", "thing=8;thought=9")
    monkeypatch.setenv("SKBUILD_NINE", "thing=8")

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
    assert settings.seven == 7
    assert settings.eight == {"thing": "8", "thought": "9"}
    assert settings.nine == {"thing": 8}


def test_conf():
    config_settings: Dict[str, Union[str, List[str]]] = {
        "zero": "zero",
        "one": "one",
        "two": "2",
        "three": ["three"],
        "four": ["4"],
        "five": "five",
        "six": "six",
        "seven": "7",
        "eight.foo": "one",
        "eight.bar": "two",
        "nine.thing": "8",
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
    assert settings.seven == 7
    assert settings.eight == {"foo": "one", "bar": "two"}
    assert settings.nine == {"thing": 8}


def test_toml():
    toml_settings = {
        "zero": "zero",
        "one": "one",
        "two": 2,
        "three": ["three"],
        "four": [4],
        "five": "five",
        "six": "six",
        "seven": 7,
        "eight": {"one": "one", "two": "two"},
        "nine": {"thing": 8},
        "ten": {"a": {"b": 3}},
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
    assert settings.seven == 7
    assert settings.eight == {"one": "one", "two": "two"}
    assert settings.nine == {"thing": 8}
    assert settings.ten == {"a": {"b": 3}}


def test_all_names():
    keys = [x.name for x in dataclasses.fields(SettingChecker)]

    envame = [f"SKBUILD_{x.upper()}" for x in keys]
    assert list(EnvSource("SKBUILD").all_option_names(SettingChecker)) == envame

    assert list(ConfSource(settings={}).all_option_names(SettingChecker)) == keys
    skkeys = [f"skbuild.{x}" for x in keys]
    assert (
        list(ConfSource("skbuild", settings={}).all_option_names(SettingChecker))
        == skkeys
    )

    assert list(TOMLSource(settings={}).all_option_names(SettingChecker)) == keys
    assert (
        list(TOMLSource("skbuild", settings={}).all_option_names(SettingChecker))
        == skkeys
    )


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
    config_settings: Dict[str, Union[str, List[str]]] = {
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


def test_all_names_nested():
    keys_two = [x.name for x in dataclasses.fields(SettingChecker)]
    ikeys = [["zero"], ["one"], *[["two", k] for k in keys_two], ["three"]]

    envame = [f"SKBUILD_{'_'.join(x).upper()}" for x in ikeys]
    assert list(EnvSource("SKBUILD").all_option_names(NestedSettingChecker)) == envame

    keys = [".".join(x) for x in ikeys]
    assert list(ConfSource(settings={}).all_option_names(NestedSettingChecker)) == keys
    skkeys = [f"skbuild.{x}" for x in keys]
    assert (
        list(ConfSource("skbuild", settings={}).all_option_names(NestedSettingChecker))
        == skkeys
    )

    assert list(TOMLSource(settings={}).all_option_names(NestedSettingChecker)) == keys
    assert (
        list(TOMLSource("skbuild", settings={}).all_option_names(NestedSettingChecker))
        == skkeys
    )


@dataclasses.dataclass
class SettingBools:
    false: bool = False
    true: bool = True


def test_env_var_bools_empty(monkeypatch):
    monkeypatch.setenv("SKBUILD_FALSE", "")
    monkeypatch.setenv("SKBUILD_TRUE", "")

    sources = SourceChain(
        EnvSource("SKBUILD"),
        ConfSource(settings={}),
        TOMLSource(settings={}),
    )
    settings = sources.convert_target(SettingBools)

    assert not settings.false
    assert settings.true


@pytest.mark.parametrize(
    ("truthy", "falsey"), [("1", "0"), ("true", "false"), ("yes", "no"), ("on", "off")]
)
def test_env_var_bools(monkeypatch, truthy, falsey):
    sources = SourceChain(
        EnvSource("SKBUILD"),
        ConfSource(settings={}),
        TOMLSource(settings={}),
    )

    monkeypatch.setenv("SKBUILD_FALSE", truthy)
    monkeypatch.setenv("SKBUILD_TRUE", falsey)

    settings = sources.convert_target(SettingBools)

    assert settings.false
    assert not settings.true


@dataclasses.dataclass
class SettingLists:
    list0: List[str] = dataclasses.field(default_factory=list)
    list1: List[str] = dataclasses.field(default_factory=list)
    list2: List[str] = dataclasses.field(default_factory=list)
    list3: List[str] = dataclasses.field(default_factory=list)
    list4: List[str] = dataclasses.field(default_factory=list)


def test_lists(monkeypatch):
    monkeypatch.setenv("SKBUILD_LIST1", "one;two;three")

    sources = SourceChain(
        EnvSource("SKBUILD"),
        ConfSource(
            settings={"list2": ["one", "two", "three"], "list3": "one;two;three"}
        ),
        TOMLSource(settings={"list4": ["one", "two", "three"]}),
    )
    settings = sources.convert_target(SettingLists)

    assert settings.list0 == []
    assert settings.list1 == ["one", "two", "three"]
    assert settings.list2 == ["one", "two", "three"]
    assert settings.list3 == ["one", "two", "three"]
    assert settings.list4 == ["one", "two", "three"]


@dataclasses.dataclass
class SettingListsOptional:
    list0: Optional[List[str]] = None
    list1: Optional[List[str]] = None
    list2: Optional[List[str]] = None
    list3: Optional[List[str]] = None
    list4: Optional[List[str]] = None


def test_lists_optional(monkeypatch):
    monkeypatch.setenv("SKBUILD_LIST1", "one;two;three")

    sources = SourceChain(
        EnvSource("SKBUILD"),
        ConfSource(
            settings={"list2": ["one", "two", "three"], "list3": "one;two;three"}
        ),
        TOMLSource(settings={"list4": ["one", "two", "three"]}),
    )
    settings = sources.convert_target(SettingListsOptional)

    assert settings.list0 is None
    assert settings.list1 == ["one", "two", "three"]
    assert settings.list2 == ["one", "two", "three"]
    assert settings.list3 == ["one", "two", "three"]
    assert settings.list4 == ["one", "two", "three"]


@pytest.mark.parametrize(
    "prefixes", [(), ("x",), ("ab", "cd"), ("x", "other")], ids=".".join
)
def test_missing_opts_conf(prefixes):
    settings = {
        "one": "one",
        "missing": "missing",
        "two.one": "one",
        "two.missing": "missing",
        "other.missing": "missing",
    }

    settings = {".".join([*prefixes, k]): v for k, v in settings.items()}
    print(settings)

    sources = SourceChain(
        EnvSource("SKBUILD"),
        ConfSource(*prefixes, settings=settings),
        TOMLSource(settings={}),
    )
    answer = ["missing", "two.missing", "other"]
    answer = [".".join([*prefixes, k]) for k in answer]
    assert list(sources.unrecognized_options(NestedSettingChecker)) == answer


def test_ignore_conf():
    settings = {
        "one": "one",
        "missing": "missing",
        "two.one": "one",
        "two.missing": "missing",
        "other.missing": "missing",
    }

    sources = SourceChain(
        EnvSource("SKBUILD"),
        ConfSource(settings=settings, verify=False),
        TOMLSource(settings={}),
    )

    assert list(sources.unrecognized_options(NestedSettingChecker)) == []


def test_missing_opts_toml():
    sources = SourceChain(
        EnvSource("SKBUILD"),
        ConfSource(settings={}),
        TOMLSource(
            "tool",
            settings={
                "tool": {
                    "one": "one",
                    "missing": "missing",
                    "two": {"one": "one", "missing": "missing"},
                    "other": {"missing": "missing"},
                },
                "things": {"thing": "x"},
            },
        ),
    )

    assert list(sources.unrecognized_options(NestedSettingChecker)) == [
        "tool.missing",
        "tool.two.missing",
        "tool.other",
    ]


@dataclasses.dataclass
class SettingsOverride:
    dict0: Dict[str, str] = dataclasses.field(default_factory=dict)
    dict1: Optional[Dict[str, int]] = None
    dict2: Optional[Dict[str, str]] = None


def test_override():
    sources = SourceChain(
        EnvSource("SKBUILD"),
        ConfSource(
            settings={"dict0.one": "one", "dict0.two": "two", "dict1.other": "2"}
        ),
        TOMLSource(settings={"dict0": {"two": "TWO", "three": "THREE"}, "dict2": {}}),
    )

    settings = sources.convert_target(SettingsOverride)

    assert settings.dict0 == {"one": "one", "two": "two", "three": "THREE"}
    assert settings.dict1 == {"other": 2}
    assert settings.dict2 == {}
