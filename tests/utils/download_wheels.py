# /// script
# dependencies = ["pip"]
# ///

"""
Download wheels into the pytest cache. Must be run from the pytest directory
(project root, usually). If run manually via a script runner, will always
include cmake/ninja. If run in an environment, requires pip.
"""

import importlib.util
import subprocess
import sys
from pathlib import Path

WHEELS = [
    "build",
    "cython",
    "hatchling",
    "pip",
    "pybind11",
    "setuptools",
    "virtualenv",
    "wheel",
]

if importlib.util.find_spec("cmake") is not None:
    WHEELS.append("cmake")

if importlib.util.find_spec("ninja") is not None:
    WHEELS.append("ninja")

if importlib.util.find_spec("pybind11") is not None:
    WHEELS.append("pybind11")


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
        capture_output=True,
        text=True,
    )
    print(f"Downloaded wheels to {wheelhouse}")


if __name__ == "__main__":
    wheelhouse = Path(".pytest_cache/d/wheelhouse")
    wheelhouse.mkdir(parents=True, exist_ok=True)
    prepare(wheelhouse)
