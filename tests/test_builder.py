import platform
import pprint
import sys
import sysconfig

import pytest

from scikit_build_core.builder.macos import get_macosx_deployment_target
from scikit_build_core.builder.sysconfig import (
    get_python_include_dir,
    get_python_library,
)


@pytest.mark.parametrize(
    "pycom,envvar,answer",
    [
        pytest.param("12.5.2", None, "12.0", id="only_plat_round"),
        pytest.param("10.12.2", None, "10.12", id="only_plat_classic"),
        pytest.param("11.2.2", "10.14", "11.0", id="env_var_lower"),
        pytest.param("10.12.2", "10.13", "10.13", id="env_var_higher"),
        pytest.param("11.2.12", "11.2", "11.0", id="same_vars_round"),
        pytest.param("10.13.2", "11", "11.0", id="env_var_no_dot"),
        pytest.param("11.2.12", "random", "11.0", id="invalid_env_var"),
        pytest.param("11.2.12", "rand.om", "11.0", id="invalid_env_var_with_dot"),
    ],
)
def test_macos_version(monkeypatch, pycom, envvar, answer):
    monkeypatch.setattr(platform, "mac_ver", lambda: (pycom,))
    if envvar is None:
        monkeypatch.delenv("MACOSX_DEPLOYMENT_TARGET", raising=False)
    else:
        monkeypatch.setenv("MACOSX_DEPLOYMENT_TARGET", envvar)

    assert get_macosx_deployment_target() == answer


def test_get_python_include_dir():
    assert get_python_include_dir().is_dir()


def test_get_python_library():
    pprint.pprint(sysconfig.get_config_vars())

    lib = get_python_library()
    if sys.platform.startswith("win"):
        assert lib is None
    else:
        assert lib
        assert lib.is_file()
