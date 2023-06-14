from __future__ import annotations

import sys
from pathlib import Path

import pytest

DIR = Path(__file__).parent
PROJECT_DIR = DIR / "packages" / "custom_cmake"


def test_ep(isolated):
    isolated.install("hatchling", "scikit-build-core[pyproject]")
    isolated.install(PROJECT_DIR / "extern", isolated=False)
    isolated.install(PROJECT_DIR, "-v", isolated=False)

    if sys.platform.startswith("win"):
        # TODO: maybe figure out how to make this work on windows?
        pytest.skip("Can't run script on Windows")

    script = isolated.run("script1", capture=True).strip()
    pysys = isolated.execute("import sys; print(sys.executable)").strip()
    contents = Path(script).read_text()
    assert contents.startswith(f"#!{pysys}")
