from __future__ import annotations

__lazy_modules__ = {
    f"{(__spec__.parent or '').rsplit('.', 1)[0]}._compat",
    f"{(__spec__.parent or '').rsplit('.', 1)[0]}.resources",
    "packaging",
    "packaging.tags",
    "typing",
}

import functools
from typing import Literal

import packaging.tags

from .._compat import tomllib
from ..resources import resources

__all__ = ["is_known_platform", "known_wheels"]


def __dir__() -> list[str]:
    return __all__


@functools.lru_cache(maxsize=2)
def known_wheels(name: Literal["ninja", "cmake"]) -> frozenset[str]:
    with resources.joinpath("known_wheels.toml").open("rb") as f:
        return frozenset(tomllib.load(f)["tool"]["scikit-build"][name]["known-wheels"])


@functools.lru_cache(maxsize=2)
def is_known_platform(platforms: frozenset[str]) -> bool:
    # Called through the module so tests can monkeypatch packaging.tags.sys_tags.
    return any(tag.platform in platforms for tag in packaging.tags.sys_tags())
