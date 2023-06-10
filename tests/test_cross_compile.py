from __future__ import annotations

import os
import subprocess
import sys
import sysconfig

import pytest

from scikit_build_core.builder.cross_compile import set_cross_compile_env

ext_suffix = sysconfig.get_config_var("EXT_SUFFIX")


@pytest.mark.skipif(
    ext_suffix != ".cp311-win_amd64.pyd",
    reason=f"Only tests '.cp311-win_amd64.pyd', got {ext_suffix!r}",
)
def test_environment():
    env = os.environ.copy()
    cmd = [
        sys.executable,
        "-c",
        "import sysconfig; print(sysconfig.get_config_var('SOABI'), sysconfig.get_config_var('EXT_SUFFIX'))",
    ]

    with set_cross_compile_env(".cp311-win_arm64.pyd", env):
        result = subprocess.run(
            cmd, check=True, capture_output=True, text=True, env=env
        )
        soabi, ext_suffix = result.stdout.strip().split()
        print(soabi, ext_suffix)
        assert soabi == "cp311-win_arm64"
        assert ext_suffix == ".cp311-win_arm64.pyd"

    result = subprocess.run(cmd, check=True, capture_output=True, text=True, env=env)
    soabi, ext_suffix = result.stdout.strip().split()
    assert soabi == "cp311-win_amd64"
    assert ext_suffix == ".cp311-win_amd64.pyd"
