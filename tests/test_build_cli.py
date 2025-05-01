from __future__ import annotations

import json
import shutil
import sys
import sysconfig
from typing import TYPE_CHECKING

import pytest

from scikit_build_core._logging import rich_warning
from scikit_build_core.build.__main__ import main

if TYPE_CHECKING:
    from pathlib import Path

PYPROJECT_1 = """
[build-system]
requires = ["scikit-build-core"]
build-backend = "scikit_build_core.build"
[project]
name = "test"
dynamic = ["version"]

[tool.scikit-build.metadata.version]
provider = "scikit_build_core.metadata.setuptools_scm"
"""


@pytest.mark.parametrize("mode", ["sdist", "wheel", "editable"])
@pytest.mark.parametrize("force_make", [False, True])
def test_requires_command(
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    mode: str,
    force_make: bool,
) -> None:
    monkeypatch.setattr(
        sys, "argv", ["scikit_build_core.build", "requires", f"--mode={mode}"]
    )
    monkeypatch.setattr(shutil, "which", lambda _: None)
    monkeypatch.delenv("CMAKE_GENERATOR", raising=False)
    monkeypatch.delenv("CMAKE_ARGS", raising=False)
    if force_make:
        monkeypatch.setenv("CMAKE_GENERATOR", "Makefiles")
    (tmp_path / "pyproject.toml").write_text(PYPROJECT_1)
    monkeypatch.chdir(tmp_path)

    main()
    rich_warning.cache_clear()
    out, err = capsys.readouterr()
    assert "CMakeLists.txt not found" in err
    jout = json.loads(out)
    if mode == "sdist":
        assert frozenset(jout) == {"scikit-build-core", "setuptools-scm"}
    elif sysconfig.get_platform().startswith("win-") or force_make:
        assert frozenset(jout) == {
            "cmake>=3.15",
            "scikit-build-core",
            "setuptools-scm",
        }
    else:
        assert frozenset(jout) == {
            "cmake>=3.15",
            "ninja>=1.5",
            "scikit-build-core",
            "setuptools-scm",
        }


PYPROJECT_2 = """
[build-system]
requires = ["scikit-build-core"]
build-backend = "scikit_build_core.build"
[project]
name = "test"
dynamic = ["version", "dependencies"]

[tool.scikit-build.metadata.version]
provider = "scikit_build_core.metadata.regex"
input = "version.py"

[tool.scikit-build.metadata.dependencies]
provider = "scikit_build_core.metadata.template"
result = ["self=={project[version]}"]
"""


def test_metadata_command(
    capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(sys, "argv", ["scikit_build_core.build", "project-table"])
    monkeypatch.setattr(shutil, "which", lambda _: None)
    (tmp_path / "pyproject.toml").write_text(PYPROJECT_2)
    (tmp_path / "version.py").write_text("version = '0.1.3'")
    monkeypatch.chdir(tmp_path)

    main()
    out, _ = capsys.readouterr()
    jout = json.loads(out)
    assert jout == {
        "name": "test",
        "version": "0.1.3",
        "dynamic": [],
        "dependencies": ["self==0.1.3"],
    }
