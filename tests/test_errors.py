from __future__ import annotations

import subprocess

from scikit_build_core.errors import FailedProcessError


def _make_error(stdout: str | bytes, stderr: str | bytes) -> FailedProcessError:
    exc = subprocess.CalledProcessError(
        returncode=1,
        cmd=["cmake", "--build", "."],
        output=stdout,
        stderr=stderr,
    )
    return FailedProcessError(exc, "Build failed")


def test_failed_process_error_str_text() -> None:
    # Subprocesses run with text=True, so streams are str. Regression: __str__
    # previously called .decode() unconditionally and raised AttributeError.
    msg = str(_make_error("out text", "err text"))
    assert "Build failed" in msg
    assert "out text" in msg
    assert "err text" in msg
    assert "return code 1" in msg


def test_failed_process_error_str_bytes() -> None:
    # Bytes streams are still decoded defensively.
    msg = str(_make_error(b"out bytes", b"err bytes"))
    assert "out bytes" in msg
    assert "err bytes" in msg
