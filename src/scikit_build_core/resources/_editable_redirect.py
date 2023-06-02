from __future__ import annotations

import importlib.abc
import importlib.machinery
import importlib.util
import os
import subprocess
import sys

DIR = os.path.abspath(os.path.dirname(__file__))
MARKER = "SKBUILD_EDITABLE_SKIP"
VERBOSE = "SKBUILD_EDITABLE_VERBOSE"

__all__ = ["install"]


def __dir__() -> list[str]:
    return __all__


class ScikitBuildRedirectingFinder(importlib.abc.MetaPathFinder):
    def __init__(
        self,
        known_source_files: dict[str, str],
        known_wheel_files: dict[str, str],
        path: str | None,
        rebuild: bool,
        verbose: bool,
        build_options: list[str],
        install_options: list[str],
    ):
        self.known_source_files = known_source_files
        self.known_wheel_files = known_wheel_files
        self.path = path
        self.rebuild_flag = rebuild
        self.verbose = verbose
        self.build_options = build_options
        self.install_options = install_options

    def find_spec(
        self,
        fullname: str,
        path: object = None,
        target: object = None,
    ) -> importlib.machinery.ModuleSpec | None:
        if fullname in self.known_wheel_files:
            redir = self.known_wheel_files[fullname]
            if self.rebuild_flag:
                self.rebuild()
            return importlib.util.spec_from_file_location(
                fullname, os.path.join(DIR, redir)
            )
        if fullname in self.known_source_files:
            redir = self.known_source_files[fullname]
            return importlib.util.spec_from_file_location(fullname, redir)

        return None

    def rebuild(self) -> None:
        # Don't rebuild if not set to a local path
        if not self.path:
            return

        env = os.environ.copy()
        # Protect against recursion
        if self.path in env.get(MARKER, "").split(os.pathsep):
            return

        env[MARKER] = os.pathsep.join((env.get(MARKER, ""), self.path))

        verbose = self.verbose or bool(env.get(VERBOSE, ""))
        if env.get(VERBOSE, "") == "0":
            verbose = False
        if verbose:
            print(f"Running cmake --build & --install in {self.path}")  # noqa: T201

        result = subprocess.run(
            ["cmake", "--build", ".", *self.build_options],
            cwd=self.path,
            stdout=sys.stderr if verbose else subprocess.PIPE,
            env=env,
            check=False,
            text=True,
        )
        if result.returncode and verbose:
            print(  # noqa: T201
                f"ERROR: {result.stdout}",
                file=sys.stderr,
            )
        result.check_returncode()

        result = subprocess.run(
            ["cmake", "--install", ".", "--prefix", DIR, *self.install_options],
            cwd=self.path,
            stdout=sys.stderr if verbose else subprocess.PIPE,
            env=env,
            check=False,
            text=True,
        )
        if result.returncode and verbose:
            print(  # noqa: T201
                f"ERROR: {result.stdout}",
                file=sys.stderr,
            )
        result.check_returncode()


def install(
    known_source_files: dict[str, str],
    known_wheel_files: dict[str, str],
    path: str | None,
    rebuild: bool = False,
    verbose: bool = False,
    build_options: list[str] | None = None,
    install_options: list[str] | None = None,
) -> None:
    """
    Install a meta path finder that redirects imports to the source files, and
    optionally rebuilds if path is given.

    :param known_source_files: A mapping of module names to source files
    :param known_wheel_files: A mapping of module names to wheel files
    :param path: The path to the build directory, or None
    :param verbose: Whether to print the cmake commands (also controlled by the
                    SKBUILD_EDITABLE_VERBOSE environment variable)
    """
    sys.meta_path.insert(
        0,
        ScikitBuildRedirectingFinder(
            known_source_files,
            known_wheel_files,
            path,
            rebuild,
            verbose,
            build_options or [],
            install_options or [],
        ),
    )
