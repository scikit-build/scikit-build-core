from __future__ import annotations

import subprocess
import sys
from pathlib import Path


def run() -> None:
    exe_path = Path(__file__).parent
    exe_path = exe_path / "bin/main"
    sys.exit(subprocess.call([str(exe_path), *sys.argv[2:]]))


if __name__ == "__main__":
    run()
