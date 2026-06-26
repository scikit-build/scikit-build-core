#!/usr/bin/env python3
# /// script
# dependencies = [
#   "virtualenv",
# ]
# ///

import argparse
import logging
import shutil
import subprocess
import sys
from os import environ
from pathlib import Path
from tempfile import TemporaryDirectory

import virtualenv

logging.basicConfig(level="INFO")
logger = logging.getLogger(Path(__file__).name)

EXAMPLES_DIR = Path(__file__).absolute().parent
ROOT_DIR = EXAMPLES_DIR.parent.parent


def main(test_name: str) -> None:
    with TemporaryDirectory(prefix="scikit-build-core-example") as tmpdir_str:
        tmpdir = Path(tmpdir_str)
        example_dir = tmpdir / "example"
        if "/getting_started/" in test_name:
            # Generate the example from the init templates (the single source of
            # truth); the last path component names the binding backend.
            backend = test_name.rstrip("/").rsplit("/", 1)[-1]
            logger.info("Generating %s example in %s", backend, example_dir)
            subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "scikit_build_core.init",
                    str(example_dir),
                    "--backend",
                    backend,
                    "--name",
                    "example",
                    "--force",
                ],
                check=True,
            )
        else:
            # Removing the `/` prefix to make it a relative path starting from `ROOT_DIR`
            example_source = ROOT_DIR / test_name.removeprefix("/")
            logger.info("Copying %s to %s", example_source, example_dir)
            shutil.copytree(example_source, example_dir)
        venv_path = tmpdir / ".venv"
        logger.info("Setting up venv")
        with virtualenv.cli_run(["--system-site-packages", str(venv_path)]) as venv:
            venv_exe = venv.creator.exe
            logger.info("Running pip install")
            subprocess.run(
                [
                    venv_exe,
                    "-m",
                    "pip",
                    "install",
                    "--no-index",
                    "--no-build-isolation",
                    "-v",
                    ".",
                ],
                check=True,
                cwd=example_dir,
            )
            if "/downstream/" in test_name:
                logger.info("Running pytest")
                subprocess.run(
                    [
                        venv_exe,
                        "-m",
                        "pytest",
                    ],
                    check=True,
                    cwd=example_dir,
                )
            elif "/getting_started/" in test_name:
                logger.info("Running common getting_started/test.py")
                test_py = EXAMPLES_DIR / "getting_started/test.py"
                subprocess.run(
                    [
                        venv_exe,
                        test_py,
                    ],
                    check=True,
                    cwd=example_dir,
                )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Docs examples test helper",
    )
    parser.add_argument(
        "--test-name", default=environ.get("TMT_TEST_NAME"), help="Test name to run"
    )
    args = parser.parse_args()
    if not args.test_name:
        logger.error("test-name was not provided")
        raise SystemExit(1)
    try:
        main(args.test_name)
    except SystemExit as err:
        logger.exception("Test failed!")
        raise SystemExit(1) from err
    except Exception as err:
        logger.exception("Test errored unexpectedly!")
        raise SystemExit(2) from err
