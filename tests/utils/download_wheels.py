# /// script
# dependencies = ["pip"]
# ///

"""
Download wheels into the pytest cache. Must be run from the pytest directory
(project root, usually). If run in an environment, requires pip. Only downloads
pybind11, ninja, or cmake if those are in the environment already.
"""

import importlib.util
import subprocess
import sys
from pathlib import Path

EXTRA = []

if importlib.util.find_spec("cmake") is not None:
    EXTRA.append("cmake")

if importlib.util.find_spec("ninja") is not None:
    EXTRA.append("ninja")

if importlib.util.find_spec("pybind11") is not None:
    EXTRA.append("pybind11")

WHEELS = [
    "build",
    "cython",
    "hatchling",
    "pip",
    "setuptools",
    "virtualenv",
    "wheel",
    *EXTRA,
]


def prepare(wheelhouse: Path) -> None:
    subprocess.run(
        [
            sys.executable,
            "-m",
            "pip",
            "download",
            "-q",
            "-d",
            str(wheelhouse),
            *WHEELS,
        ],
        check=True,
    )
    print(f"Downloaded wheels to {wheelhouse}")


if __name__ == "__main__":
    wheelhouse = Path(".pytest_cache/d/wheelhouse")
    wheelhouse.mkdir(parents=True, exist_ok=True)
    prepare(wheelhouse)
