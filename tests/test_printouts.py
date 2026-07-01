from __future__ import annotations

import sys

from scikit_build_core.builder.__main__ import main

TYPE_CHECKING = False
if TYPE_CHECKING:
    import pytest


def test_builder_printout(
    capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(sys, "argv", ["scikit_build_core.builder"])
    main()
    out, _ = capsys.readouterr()
    assert "Detected Python Library" in out


def test_builder_module_wheel_tag(
    capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    # Regression test: ``python -m scikit_build_core.builder <subcommand>`` used to
    # silently ignore its arguments and always print the full info dump.
    monkeypatch.setattr(
        sys, "argv", ["scikit_build_core.builder", "wheel-tag", "--purelib"]
    )
    main()
    out, _ = capsys.readouterr()
    assert out.strip() == "py3-none-any"
