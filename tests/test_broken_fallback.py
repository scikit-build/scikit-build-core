import zipfile
from pathlib import Path

import pytest

from scikit_build_core.build import (
    build_wheel,
    get_requires_for_build_wheel,
)


@pytest.mark.compile
@pytest.mark.configure
@pytest.mark.usefixtures("broken_fallback")
@pytest.mark.parametrize("broken_define", ["BROKEN_CMAKE", "BROKEN_CODE"])
def test_broken_code(
    broken_define: str, capfd: pytest.CaptureFixture[str], tmp_path: Path
):
    dist = tmp_path / "dist"
    build_wheel(str(dist), {f"cmake.define.{broken_define}": "1"})
    wheel = dist / "broken_fallback-0.0.1-py3-none-any.whl"
    with zipfile.ZipFile(wheel) as f:
        file_names = set(f.namelist())

    assert file_names == {
        "broken_fallback-0.0.1.dist-info/RECORD",
        "broken_fallback-0.0.1.dist-info/WHEEL",
        "broken_fallback-0.0.1.dist-info/METADATA",
    }

    out, err = capfd.readouterr()
    assert "retrying due to override..." in out

    if broken_define == "BROKEN_CMAKE":
        assert "Broken CMake" in err
        assert "CMake Error at CMakeLists.txt" in err
        assert "CMake configuration failed" in out
    else:
        assert "CMake build failed" in out


@pytest.mark.usefixtures("broken_fallback")
def test_fail_setting(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
):
    monkeypatch.setenv("FAIL_NOW", "1")

    assert get_requires_for_build_wheel({}) == []
    with pytest.raises(SystemExit) as exc:
        build_wheel("dist")

    assert exc.value.code == 7
    _, err = capsys.readouterr()
    assert "fail setting was enabled" in err


@pytest.mark.usefixtures("broken_fallback")
def test_fail_setting_msg(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
):
    monkeypatch.setenv("FAIL_NOW", "1")
    monkeypatch.setenv(
        "SKBUILD_MESSAGES_AFTER_FAILURE", "This is a test failure message"
    )

    assert get_requires_for_build_wheel({}) == []
    with pytest.raises(SystemExit) as exc:
        build_wheel("dist")

    assert exc.value.code == 7
    out, _ = capsys.readouterr()
    assert "This is a test failure message" in out
    assert "fail setting was enabled" not in out
