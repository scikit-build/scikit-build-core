from __future__ import annotations

from typing import TYPE_CHECKING

from scikit_build_core.builder.__main__ import main

if TYPE_CHECKING:
    import pytest


def test_builder_printout(capsys: pytest.CaptureFixture[str]) -> None:
    main()
    out, err = capsys.readouterr()
    assert "Detected Python Library" in out
