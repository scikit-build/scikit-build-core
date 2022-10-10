import os
import subprocess
import sys
from pathlib import Path

DIR = Path(__file__).parent.resolve()


def test_cattrs_converter():
    env = os.environ.copy()
    if "FORCE_COLOR" in env:
        del env["FORCE_COLOR"]
    out = subprocess.run(
        [
            sys.executable,
            "-m",
            "scikit_build_core.file_api._cattrs_converter",
            str(DIR / "api/simple_pure/.cmake/api/v1/reply"),
        ],
        check=True,
        env=env,
        stdout=subprocess.PIPE,
        text=True,
    )
    assert "version=CMakeVersion" in out.stdout
    assert "toolchains_v1=Toolchains(" in out.stdout


def test_query(tmp_path):
    env = os.environ.copy()
    if "FORCE_COLOR" in env:
        del env["FORCE_COLOR"]
    build_dir = tmp_path / "test_query"
    build_dir.mkdir()
    out = subprocess.run(
        [sys.executable, "-m", "scikit_build_core.file_api.query", str(build_dir)],
        check=True,
        env=env,
        stdout=subprocess.PIPE,
        text=True,
    )
    api_dir = build_dir / ".cmake/api/v1"
    query_dir = api_dir / "query"
    assert query_dir.joinpath("codemodel-v2").is_file()
    assert query_dir.joinpath("cache-v2").is_file()
    assert query_dir.joinpath("cmakeFiles-v1").is_file()
    assert query_dir.joinpath("toolchains-v1").is_file()
    assert str(api_dir / "reply") == out.stdout.strip()


def test_reply():
    env = os.environ.copy()
    if "FORCE_COLOR" in env:
        del env["FORCE_COLOR"]
    out = subprocess.run(
        [
            sys.executable,
            "-m",
            "scikit_build_core.file_api.reply",
            str(DIR / "api/simple_pure/.cmake/api/v1/reply"),
        ],
        check=True,
        env=env,
        stdout=subprocess.PIPE,
        text=True,
    )
    assert "version=CMakeVersion" in out.stdout
    assert "toolchains_v1=Toolchains(" in out.stdout
