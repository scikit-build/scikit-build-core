from __future__ import annotations

import re

from packaging.specifiers import SpecifierSet

__all__ = ["find_min_cmake_version"]


def __dir__() -> list[str]:
    return __all__


PATTERN = re.compile(
    r"""
    ^                              # Match start of line
    \s*
    cmake_minimum_required         # Match the command
    \s*
    \(                             # Match opening parenthesis
    (.*?)                          # Capture any contents (note: fancy strings, etc. should not be present)
    \)                             # Closing
    """,
    re.VERBOSE | re.MULTILINE | re.DOTALL | re.IGNORECASE,
)


def find_min_cmake_version(cmake_content: str) -> SpecifierSet | None:
    """
    Locate the minimum required version. Return None if not found.
    """
    result = PATTERN.search(cmake_content)
    if not result:
        return None

    ver_str = (
        result.group(1)
        .replace("VERSION", "")
        .replace("FATAL_ERROR", "")
        .split("...")[0]
        .strip()
        .strip("\"'[]=")
    )

    return SpecifierSet(f">={ver_str}")
