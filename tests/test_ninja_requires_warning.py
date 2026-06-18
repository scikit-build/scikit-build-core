"""
Regression tests for issue #953: the "ninja should not be in
build-system.requires" warning must only fire when scikit-build-core would
actually fall back to providing ninja itself.  When the user has pinned a
Ninja generator or disabled make-fallback, ninja is genuinely required and
the warning is misleading.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from scikit_build_core.build.wheel import _build_wheel_impl

if TYPE_CHECKING:
    from pathlib import Path

    import pytest

PYPROJECT_TEMPLATE = """\
[build-system]
requires = ["scikit-build-core", {extra_requires}]
build-backend = "scikit_build_core.build"

[project]
name = "dummy"
version = "0.1.0"

[tool.scikit-build]
wheel.cmake = false
{skbuild_extras}
"""


def _run(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    extra_requires: str = "",
    skbuild_extras: str = "",
) -> None:
    """Write a minimal pyproject.toml and call _build_wheel_impl for metadata only."""
    monkeypatch.chdir(tmp_path)
    (tmp_path / "pyproject.toml").write_text(
        PYPROJECT_TEMPLATE.format(
            extra_requires=extra_requires,
            skbuild_extras=skbuild_extras,
        ),
        encoding="utf-8",
    )
    mddir = tmp_path / "dist"
    mddir.mkdir()
    _build_wheel_impl(None, {}, str(mddir), editable=False)


def _ninja_warning_messages(caplog: pytest.LogCaptureFixture) -> list[str]:
    return [
        str(r.message)
        for r in caplog.records
        if "ninja" in str(r.message) and "build-system.requires" in str(r.message)
    ]


def test_ninja_in_requires_warns_by_default(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Warning fires when ninja is in requires and make-fallback is on (default)."""
    with caplog.at_level(logging.WARNING, logger="scikit_build_core"):
        _run(tmp_path, monkeypatch, extra_requires='"ninja>=1.5"')

    msgs = _ninja_warning_messages(caplog)
    assert msgs, "Expected a ninja warning but got none"


def test_ninja_in_requires_no_warn_when_make_fallback_disabled(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """No warning when ninja.make-fallback is false — ninja is strictly required."""
    with caplog.at_level(logging.WARNING, logger="scikit_build_core"):
        _run(
            tmp_path,
            monkeypatch,
            extra_requires='"ninja>=1.5"',
            skbuild_extras="ninja.make-fallback = false",
        )

    msgs = _ninja_warning_messages(caplog)
    assert not msgs, f"Unexpected ninja warning(s): {msgs}"


def test_ninja_in_requires_no_warn_when_ninja_generator_forced(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """No warning when the user explicitly forces -GNinja (make fallback disabled)."""
    monkeypatch.delenv("CMAKE_GENERATOR", raising=False)
    with caplog.at_level(logging.WARNING, logger="scikit_build_core"):
        _run(
            tmp_path,
            monkeypatch,
            extra_requires='"ninja>=1.5"',
            skbuild_extras='cmake.args = ["-GNinja"]',
        )

    msgs = _ninja_warning_messages(caplog)
    assert not msgs, f"Unexpected ninja warning(s): {msgs}"
