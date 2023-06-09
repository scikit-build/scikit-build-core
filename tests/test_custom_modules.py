from __future__ import annotations

from pathlib import Path

DIR = Path(__file__).parent
PROJECT_DIR = DIR / "packages" / "custom_cmake"


def test_ep(isolated):
    isolated.install("hatchling", "scikit-build-core[pyproject]")
    isolated.install(PROJECT_DIR / "extern", isolated=False)
    isolated.install(PROJECT_DIR, "-v", isolated=False)
    script = isolated.run("script1", capture=True).strip()
    pysys = isolated.execute("import sys; print(sys.executable)").strip()
    contents = Path(script).read_text()
    assert contents.startswith(f"#!{pysys}")
