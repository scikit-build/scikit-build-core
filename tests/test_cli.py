from __future__ import annotations

from scikit_build_core.__main__ import main

TYPE_CHECKING = False
if TYPE_CHECKING:
    from pathlib import Path

    import pytest


def test_cli_no_args(capsys: pytest.CaptureFixture[str]) -> None:
    main([])
    out, _ = capsys.readouterr()
    assert "scikit-build build requires" in out
    assert "scikit-build builder" in out
    assert "scikit-build file-api" in out
    assert "scikit-build init" in out


def test_cli_builder(capsys: pytest.CaptureFixture[str]) -> None:
    main(["builder"])
    out, _ = capsys.readouterr()
    assert "Detected Python Library" in out


def test_cli_builder_sysconfig(capsys: pytest.CaptureFixture[str]) -> None:
    main(["builder", "sysconfig"])
    out, _ = capsys.readouterr()
    assert "Detected Python Library" in out


def test_cli_builder_wheel_tag(capsys: pytest.CaptureFixture[str]) -> None:
    main(["builder", "wheel-tag", "--purelib"])
    out, _ = capsys.readouterr()
    assert out.strip() == "py3-none-any"


def test_cli_file_api_query(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    build_dir = tmp_path / "build"
    main(["file-api", "query", str(build_dir)])
    out, _ = capsys.readouterr()
    query_dir = build_dir / ".cmake/api/v1/query"
    assert query_dir.joinpath("codemodel-v2").is_file()
    assert out.strip().endswith("reply")


def test_cli_build_requires(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    pyproject = (
        "[build-system]\n"
        'requires = ["scikit-build-core"]\n'
        'build-backend = "scikit_build_core.build"\n'
        "[project]\n"
        'name = "test"\n'
        'version = "0.1.0"\n'
    )
    (tmp_path / "pyproject.toml").write_text(pyproject)
    monkeypatch.chdir(tmp_path)
    main(["build", "requires", "--mode=sdist"])
    out, _ = capsys.readouterr()
    assert "scikit-build-core" in out
