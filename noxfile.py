"""
Scikit-build-core's nox configuration.

Use `-t gen` to run all the generation jobs.
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
import urllib.request
from pathlib import Path
from typing import TYPE_CHECKING

import nox

if TYPE_CHECKING:
    from collections.abc import Sequence

nox.needs_version = ">=2024.4.15"
nox.options.default_venv_backend = "uv|virtualenv"

DIR = Path(__file__).parent.resolve()


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
    session.install("-e.[dev,test,test-meta]", "pylint==3.3.*")
    session.run("pylint", "--version")
    session.run("pylint", "scikit_build_core", *session.posargs)


def _prepare_cmake_ninja(
    session: nox.Session,
) -> None:
    # This will not work if system CMake is too old (<3.15)
    if shutil.which("cmake") is None and shutil.which("cmake3") is None:
        session.install("cmake")
    if shutil.which("ninja") is None:
        session.install("ninja")


def _run_tests(
    session: nox.Session,
    *,
    install_args: Sequence[str] = (),
    run_args: Sequence[str] = (),
    extras: Sequence[str] = (),
) -> None:
    posargs = list(session.posargs) or ["-n", "auto"]
    env = {"PIP_DISABLE_PIP_VERSION_CHECK": "1"}

    _prepare_cmake_ninja(session)

    _extras = ["test", *extras]
    if "--cov" in posargs:
        _extras.append("cov")
        posargs.append("--cov-config=pyproject.toml")

    install_arg = f"-e.[{','.join(_extras)}]"
    session.install(install_arg, *install_args, "pytest-xdist", silent=False)
    session.run("pytest", *run_args, *posargs, env=env)


@nox.session(reuse_venv=True, tags=["gen"])
def generate_schema(session: nox.Session) -> None:
    """
    (Re)generate src/scikit_build_core/resources/scikit-build.schema.json from model.
    """
    session.install("-e.")
    schema_txt = session.run(
        "python", "-m", "scikit_build_core.settings.skbuild_schema", silent=True
    )
    assert isinstance(schema_txt, str)
    schema_file = DIR / "src/scikit_build_core/resources/scikit-build.schema.json"
    schema_file.write_text(schema_txt)


@nox.session
def tests(session: nox.Session) -> None:
    """
    Run the unit and regular tests. Includes coverage if --cov passed.
    """
    _run_tests(session, extras=["test-meta,test-numpy,test-schema,test-hatchling"])


@nox.session(reuse_venv=True, tags=["gen"])
def readme(session: nox.Session) -> None:
    """
    Update the readme with cog. Pass --check to check instead.
    """

    args = session.posargs or ["-r"]

    session.install("-e.", "cogapp")
    session.run("cog", "-P", *args, "README.md")


@nox.session(venv_backend="uv", default=False)
def minimums(session: nox.Session) -> None:
    """
    Test the minimum versions of dependencies.
    """

    _run_tests(
        session,
        install_args=["--resolution=lowest-direct"],
        run_args=["-Wdefault"],
    )


@nox.session(reuse_venv=True, default=False)
def docs(session: nox.Session) -> None:
    """
    Build the docs. Use "--non-interactive" to avoid serving. Pass "-b linkcheck" to check links.
    """

    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-b", dest="builder", default="html", help="Build target (default: html)"
    )
    args, posargs = parser.parse_known_args(session.posargs)

    serve = args.builder == "html" and session.interactive
    extra_installs = ["sphinx-autobuild"] if serve else []
    session.install("-e.[docs]", *extra_installs)

    session.chdir("docs")

    shared_args = (
        "-n",  # nitpicky mode
        "-T",  # full tracebacks
        f"-b={args.builder}",
        ".",
        f"_build/{args.builder}",
        *posargs,
    )

    if serve:
        session.run("sphinx-autobuild", "--open-browser", *shared_args)
    else:
        session.run("sphinx-build", "--keep-going", *shared_args)


@nox.session(tags=["gen"])
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


@nox.session(default=False)
def build(session: nox.Session) -> None:
    """
    Build an SDist and wheel.
    """

    session.install("build")
    session.run("python", "-m", "build", *session.posargs)


EXAMPLES = ["c", "abi3", "pybind11", "nanobind", "swig", "cython"]
if not sys.platform.startswith("win") and shutil.which("gfortran"):
    EXAMPLES.append("fortran")
EXAMPLES = [f"getting_started/{n}" for n in EXAMPLES]
EXAMPLES += ["downstream/pybind11_example", "downstream/nanobind_example"]


@nox.session
@nox.parametrize("example", EXAMPLES, ids=EXAMPLES)
def test_doc_examples(session: nox.Session, example: str) -> None:
    _prepare_cmake_ninja(session)
    session.install("-e.", "pip")
    session.chdir(f"docs/examples/{example}")
    reqs = nox.project.load_toml("pyproject.toml")["build-system"]["requires"]
    freqs = (r for r in reqs if "scikit-build-core" not in r.replace("_", "-"))
    session.install(*freqs, "pytest")
    session.install(
        ".",
        "--no-build-isolation",
        "--config-settings=cmake.verbose=true",
        env={"PYTHONWARNINGS": "error"},
    )
    session.run("pip", "list")
    if Path("../test.py").is_file():
        session.run("python", "../test.py")
    else:
        session.run("pytest")


@nox.session(default=False)
def downstream(session: nox.Session) -> None:
    """
    Build a downstream project.
    """

    # If running in manylinux:
    #   docker run --rm -v $PWD:/sk -w /sk -t quay.io/pypa/manylinux2014_x86_64:latest \
    #       pipx run nox -s downstream -- https://github.com/...

    parser = argparse.ArgumentParser(prog=f"{Path(sys.argv[0]).name} -s downstream")
    parser.add_argument("project", help="A project to build")
    parser.add_argument("--subdir", help="A subdirectory to build")
    parser.add_argument(
        "--editable", action="store_true", help="Install as editable wheel"
    )
    parser.add_argument("-c", dest="code", help="Run some Python code")
    parser.add_argument("-C", help="config-settings", action="append", default=[])
    args, remaining = parser.parse_known_args(session.posargs)

    tmp_dir = Path(session.create_tmp())
    proj_dir = tmp_dir / "_".join(args.project.split("/"))

    session.install("build", "hatch-vcs", "hatchling")
    session.install(".", "--no-build-isolation")

    if proj_dir.is_dir():
        session.chdir(proj_dir)
        session.run("git", "pull", external=True)
    else:
        session.run(
            "git",
            "clone",
            args.project,
            *remaining,
            str(proj_dir),
            "--recurse-submodules",
            external=True,
        )
        session.chdir(proj_dir)

    # Read and strip requirements
    pyproject = nox.project.load_toml("pyproject.toml")
    requires = [
        x
        for x in pyproject["build-system"]["requires"]
        if "scikit-build-core" not in x.replace("_", "-")
    ]
    if not shutil.which("ninja"):
        requires.append("ninja")
    if not shutil.which("cmake"):
        requires.append("cmake")
    if requires:
        session.install(*requires)

    if args.subdir:
        session.chdir(args.subdir)

    if args.editable:
        session.install("-e.", "--no-build-isolation")
    else:
        session.run(
            "python",
            "-m",
            "build",
            "--no-isolation",
            "--skip-dependency-check",
            "--wheel",
            ".",
            *(f"-C{x}" for x in args.C),
        )
        if args.code:
            session.error("Must use editable install for code at the moment")

    if args.code:
        session.run("python", "-c", args.code)


@nox.session(venv_backend="none", default=False)
def vendor_pyproject_metadata(session: nox.Session) -> None:
    """
    Vendor pyproject.toml metadata.
    """

    parser = argparse.ArgumentParser(
        prog=f"{Path(sys.argv[0]).name} -s vendor_pyproject_metadata"
    )
    parser.add_argument("version", help="A tag or ref to vendor")
    args = parser.parse_args(session.posargs)

    repo = "pypa/pyproject-metadata"
    branch = args.version

    with urllib.request.urlopen(
        f"https://api.github.com/repos/{repo}/git/trees/{branch}?recursive=1"
    ) as response:
        info = json.loads(response.read().decode("utf-8"))

    files = {
        y: y for x in info["tree"] if (y := x["path"]).startswith("pyproject_metadata/")
    }
    files["pyproject_metadata/LICENSE"] = "LICENSE"
    for tgt_path, remote_path in files.items():
        local_path = Path("src/scikit_build_core/_vendor").joinpath(tgt_path)
        print(f"Vendoring: {remote_path} -> {local_path}")
        with urllib.request.urlopen(
            f"https://raw.githubusercontent.com/{repo}/{branch}/{remote_path}"
        ) as response:
            txt = response.read()
        local_path.write_bytes(txt)
