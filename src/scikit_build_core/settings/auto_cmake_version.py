from __future__ import annotations

from ..ast.ast import parse
from ..ast.tokenizer import tokenize

__all__ = ["find_min_cmake_version"]


def __dir__() -> list[str]:
    return __all__


def find_min_cmake_version(cmake_content: str) -> str | None:
    """
    Locate the minimum required version. Return None if not found.
    """
    for node in parse(tokenize(cmake_content)):
        if node.name == "cmake_minimum_required":
            return (
                node.value.replace("VERSION", "")
                .replace("FATAL_ERROR", "")
                .split("...")[0]
                .strip()
                .strip("\"'[]=")
            )

    return None
