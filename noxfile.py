from __future__ import annotations

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
    session.install("-e.[dev,test]", "pylint")
    session.run("pylint", "src", *session.posargs)


@nox.session(reuse_venv=True)
def tests(session: nox.Session) -> None:
    """
    Run the unit and regular tests.
    """
    env = {"PIP_DISABLE_PIP_VERSION_CHECK": "1"}
    session.install("-e.[test]")
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

    session.install(".[docs]")
    session.chdir("docs")
    session.run("sphinx-build", "-M", "html", ".", "_build")

    if session.posargs:
        if "--serve" in session.posargs:
            print("Launching docs at http://localhost:8000/ - use Ctrl-C to quit")
            session.run("python", "-m", "http.server", "8000", "-d", "_build/html")
        else:
            session.warn("Unsupported argument to docs")


@nox.session
def build(session: nox.Session) -> None:
    """
    Build an SDist and wheel.
    """

    session.install("build")
    session.run("python", "-m", "build", **session.posargs)
