from __future__ import annotations

import subprocess

from scikit_build_core.errors import (
    CMakeAccessError,
    CMakeConfigError,
    CMakeNotFoundError,
    CMakeVersionError,
    FailedLiveProcessError,
    FailedProcessError,
    NinjaNotFoundError,
    NinjaVersionError,
    NotFoundError,
    ScikitBuildError,
)


class FakeCalledProcessError(subprocess.CalledProcessError):
    """Simple re-implementation to avoid subprocess internals."""

    def __init__(
        self, returncode: int, cmd: list[str], stdout: bytes = b"", stderr: bytes = b""
    ) -> None:
        super().__init__(returncode, cmd)
        self.stdout = stdout
        self.stderr = stderr


def test_failed_process_error_str():
    exc = FakeCalledProcessError(
        1, ["cmake", "--version"], stdout=b"out\n", stderr=b"err\n"
    )
    err = FailedProcessError(exc, "Build failed")
    msg = str(err)
    assert "Build failed" in msg
    assert "'cmake --version'" in msg
    assert "return code 1" in msg
    assert "stdout:\n    out" in msg
    assert "stderr:\n    err" in msg


def test_failed_process_error_no_output():
    exc = FakeCalledProcessError(1, ["cmake"])
    err = FailedProcessError(exc, "Build failed")
    msg = str(err)
    assert "stdout" not in msg
    assert "stderr" not in msg


def test_failed_live_process_error():
    err = FailedLiveProcessError("msg", msg="live")
    assert str(err) == "msg"
    assert err.msg == "live"


def test_exception_hierarchy():
    assert issubclass(CMakeNotFoundError, NotFoundError)
    assert issubclass(NinjaNotFoundError, NotFoundError)
    assert issubclass(NotFoundError, ScikitBuildError)
    assert issubclass(CMakeAccessError, FailedProcessError)
    assert issubclass(CMakeVersionError, ScikitBuildError)
    assert issubclass(NinjaVersionError, ScikitBuildError)
    assert issubclass(CMakeConfigError, ScikitBuildError)


def test_dir():
    from scikit_build_core import errors

    assert "ScikitBuildError" in errors.__dir__()
