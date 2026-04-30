from __future__ import annotations

import subprocess
import sys


def test_main_cli():
    result = subprocess.run(
        [sys.executable, "-m", "scikit_build_core"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0
    assert "A top level CLI is not currently provided" in result.stdout
    assert "scikit_build_core.build requires" in result.stdout
