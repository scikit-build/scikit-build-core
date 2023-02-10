from __future__ import annotations

import importlib.abc
import importlib.machinery
import importlib.util
import os
import sys

DIR = os.path.abspath(os.path.dirname(__file__))

__all__ = ["install"]


def __dir__() -> list[str]:
    return __all__


class ScikitBuildRedirectingFinder:
    def __init__(
        self, known_source_files: dict[str, str], known_wheel_files: dict[str, str]
    ):
        self.known_source_files = known_source_files
        self.known_wheel_files = known_wheel_files

    def find_spec(
        self,
        fullname: str,
        path: object = None,
        target: object = None,
    ) -> importlib.machinery.ModuleSpec | None:
        if fullname in self.known_source_files:
            redir = self.known_source_files[fullname]
            return importlib.util.spec_from_file_location(fullname, redir)
        if fullname in self.known_wheel_files:
            redir = self.known_wheel_files[fullname]
            return importlib.util.spec_from_file_location(
                fullname, os.path.join(DIR, redir)
            )

        return None


def install(
    known_source_files: dict[str, str], known_wheel_files: dict[str, str]
) -> None:
    sys.meta_path.insert(
        0, ScikitBuildRedirectingFinder(known_source_files, known_wheel_files)
    )
