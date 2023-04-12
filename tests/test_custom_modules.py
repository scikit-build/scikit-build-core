from __future__ import annotations

from pathlib import Path

DIR = Path(__file__).parent
PROJECT_DIR = DIR / "packages" / "custom_cmake"


def test_ep(isolated):
    isolated.install("hatchling", "scikit-build-core[pyproject]")
    isolated.install(PROJECT_DIR / "extern", isolated=False)
    isolated.install(PROJECT_DIR, "-v", isolated=False)
    # Needs script fix: assert isolated.run("script1") == ""
