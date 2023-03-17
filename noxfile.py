from __future__ import annotations

import argparse
import shutil
from pathlib import Path

import nox

DIR = Path(__file__).parent.resolve()

nox.options.sessions = ["lint", "pylint", "tests"]


@nox.session(reuse_venv=True)
def lint(session: nox.Session) -> None:
    """
    Run the linter.
    """
    session.install("pre-commit")
    session.run("pre-commit", "run", "--all-files", *session.posargs)


@nox.session(reuse_venv=True)
def pylint(session: nox.Session) -> None:
    """
    Run PyLint.
    """
    # This needs to be installed into the package environment, and is slower
    # than a pre-commit check
    session.install(
        "-e.[dev,test]", "pylint", "hatch-fancy-pypi-readme", "setuptools-scm"
    )
    session.run("pylint", "scikit_build_core", *session.posargs)


@nox.session(reuse_venv=True)
def tests(session: nox.Session) -> None:
    """
    Run the unit and regular tests.
    """
    env = {"PIP_DISABLE_PIP_VERSION_CHECK": "1"}
    extra = ["hatch-fancy-pypi-readme", "rich", "setuptools-scm"]
    # This will not work if system CMake is too old (<3.15)
    if shutil.which("cmake") is None and shutil.which("cmake3") is None:
        extra.append("cmake")
    if shutil.which("ninja") is None:
        extra.append("ninja")

    session.install("-e.[test]", *extra)
    session.run("pytest", *session.posargs, env=env)


@nox.session(reuse_venv=True)
def coverage(session: nox.Session) -> None:
    """
    Run coverage and report.
    """

    session.install("-e.[test,cov]")
    session.run("pytest", "--cov=scikit_build_core", *session.posargs)


@nox.session
def docs(session: nox.Session) -> None:
    """
    Build the docs. Pass "--serve" to serve.
    """

    parser = argparse.ArgumentParser()
    parser.add_argument("--serve", action="store_true", help="Serve after building")
    args = parser.parse_args(session.posargs)

    session.install(".[docs,pyproject]")
    session.chdir("docs")
    session.run("sphinx-build", "-M", "html", ".", "_build")

    if args.serve:
        print("Launching docs at http://localhost:8000/ - use Ctrl-C to quit")
        session.run("python", "-m", "http.server", "8000", "-d", "_build/html")


@nox.session
def build_api_docs(session: nox.Session) -> None:
    """
    Build (regenerate) API docs.
    """

    session.install("sphinx")
    session.chdir("docs")
    session.run(
        "sphinx-apidoc",
        "-o",
        "api/",
        "--no-toc",
        "--force",
        "--module-first",
        "../src/scikit_build_core",
    )


@nox.session
def build(session: nox.Session) -> None:
    """
    Build an SDist and wheel.
    """

    session.install("build")
    session.run("python", "-m", "build", **session.posargs)
