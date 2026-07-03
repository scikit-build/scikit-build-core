"""Unit tests for helpers in the repo-root noxfile.py.

``nox`` is not a test dependency, so the module (which imports nox and defines
sessions at import time) is loaded with a minimal stub injected into
``sys.modules``. That keeps the pure ``downstream_dir_name`` helper testable
without pulling nox into the test env.
"""

from __future__ import annotations

import importlib.util
import sys
import types
from pathlib import Path

import pytest

ROOT = Path(__file__).parent.parent
NOXFILE = ROOT / "noxfile.py"


def _load_noxfile() -> types.ModuleType:
    nox_stub = types.ModuleType("nox")

    def session(*_args: object, **_kwargs: object):
        def decorator(func: object) -> object:
            return func

        return decorator

    def parametrize(*_args: object, **_kwargs: object):
        def decorator(func: object) -> object:
            return func

        return decorator

    nox_stub.session = session  # type: ignore[attr-defined]
    nox_stub.parametrize = parametrize  # type: ignore[attr-defined]
    nox_stub.needs_version = ""  # type: ignore[attr-defined]
    nox_stub.options = types.SimpleNamespace()  # type: ignore[attr-defined]
    nox_stub.project = types.SimpleNamespace()  # type: ignore[attr-defined]

    saved = sys.modules.get("nox")
    sys.modules["nox"] = nox_stub
    try:
        spec = importlib.util.spec_from_file_location("_skbc_noxfile", NOXFILE)
        assert spec is not None
        assert spec.loader is not None
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
    finally:
        if saved is None:
            del sys.modules["nox"]
        else:
            sys.modules["nox"] = saved
    return module


noxfile = _load_noxfile()


@pytest.mark.parametrize(
    ("project", "expected"),
    [
        ("https://github.com/org/repo", "https_github.com_org_repo"),
        ("git@github.com:org/repo.git", "git_github.com_org_repo"),
        ("/home/user/projects/repo", "home_user_projects_repo"),
    ],
)
def test_downstream_dir_name(project: str, expected: str) -> None:
    assert noxfile.downstream_dir_name(project) == expected


def test_downstream_dir_name_has_no_colon() -> None:
    # Regression: an embedded ':' confused pyproject_hooks splitting backend-path.
    url = "https://github.com/scikit-build/ninja-python-distributions"
    result = noxfile.downstream_dir_name(url)
    assert ":" not in result
    assert "/" not in result


def test_downstream_dir_name_stable_across_runs() -> None:
    url = "https://github.com/scikit-build/ninja-python-distributions.git"
    assert noxfile.downstream_dir_name(url) == noxfile.downstream_dir_name(url)
