from __future__ import annotations

import platform
import sys
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pytest import CaptureFixture, MonkeyPatch

import scikit_build_core._logging
from scikit_build_core import __version__
from scikit_build_core._logging import Style, rich_print


def test_rich_print_nocolor(capsys: CaptureFixture[str], monkeypatch: MonkeyPatch):
    monkeypatch.setenv("NO_COLOR", "1")
    monkeypatch.delenv("FORCE_COLOR", raising=False)
    monkeypatch.setattr(scikit_build_core._logging, "_style", Style())
    rich_print("{red}hello{default} world", end="")
    assert capsys.readouterr().out == "hello world"


def test_rich_print_nocolor_forcecolor(
    capsys: CaptureFixture[str], monkeypatch: MonkeyPatch
):
    monkeypatch.setenv("NO_COLOR", "1")
    monkeypatch.setenv("FORCE_COLOR", "1")
    monkeypatch.setattr(scikit_build_core._logging, "_style", Style())
    rich_print("{red}hello{default} world", end="")
    assert capsys.readouterr().out == "hello world"


def test_rich_print_forcecolor(capsys: CaptureFixture[str], monkeypatch: MonkeyPatch):
    monkeypatch.setenv("FORCE_COLOR", "1")
    monkeypatch.delenv("NO_COLOR", raising=False)
    monkeypatch.setattr(scikit_build_core._logging, "_style", Style())
    rich_print("{bold.red}hello{normal} world", end="")
    assert capsys.readouterr().out == "\33[1;31mhello\33[22m world\33[0m"


def test_rich_print_fgbg(capsys: CaptureFixture[str], monkeypatch: MonkeyPatch):
    monkeypatch.setattr(scikit_build_core._logging, "_style", Style(color=True))
    rich_print("{bold.fg.red.bg.blue}hello world", end="")
    assert capsys.readouterr().out == "\33[1;31;44mhello world\33[0m"


def test_rich_notrichbrackets(capsys: CaptureFixture[str], monkeypatch: MonkeyPatch):
    monkeypatch.setattr(scikit_build_core._logging, "_style", Style(color=True))
    rich_print("{bold.red}hello{normal} world{default} [notrich]", end="")
    assert (
        capsys.readouterr().out == "\33[1;31mhello\33[22m world\33[39m [notrich]\33[0m"
    )


def test_rich_print_subs(capsys: CaptureFixture[str], monkeypatch: MonkeyPatch):
    monkeypatch.setattr(scikit_build_core._logging, "_style", Style(color=True))
    rich_print("{platform.platform} {__version__} {sys.version}", end="")
    assert (
        capsys.readouterr().out == f"{platform.platform()} {__version__} {sys.version}"
    )


def test_rich_print_each_color(capsys: CaptureFixture[str], monkeypatch: MonkeyPatch):
    monkeypatch.setattr(scikit_build_core._logging, "_style", Style(color=True))
    rich_print("hello", "world", color="green", end="")
    assert capsys.readouterr().out == "\33[32mhello\33[0m \33[32mworld\33[0m"


def test_rich_print_internal_color(
    capsys: CaptureFixture[str], monkeypatch: MonkeyPatch
):
    monkeypatch.setattr(scikit_build_core._logging, "_style", Style(color=True))
    rich_print("hello {color}world", color="green", end="")
    assert capsys.readouterr().out == "\33[32mhello \33[32mworld\33[0m"
