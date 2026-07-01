from __future__ import annotations

from scikit_build_core.builder.__main__ import main

TYPE_CHECKING = False
if TYPE_CHECKING:
    import pytest


def test_builder_printout(capsys: pytest.CaptureFixture[str]) -> None:
    main()
    out, _ = capsys.readouterr()
    assert "Detected Python Library" in out
