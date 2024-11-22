from __future__ import annotations

import dataclasses
import enum
import re
import sys
from pathlib import Path
from typing import TYPE_CHECKING

from .._logging import rich_print

if TYPE_CHECKING:
    from collections.abc import Generator

__all__ = ["Token", "TokenType", "tokenize"]


def __dir__() -> list[str]:
    return __all__


TOKEN_EXPRS = {
    "BRACKET_COMMENT": r"\s*#\[(?P<bc1>=*)\[(?s:.)*?\](?P=bc1)\]",
    "COMMENT": r"#.*$",
    "QUOTED": r'"(?:\\(?s:.)|[^"\\])*?"',
    "BRACKET_QUOTE": r"\[(?P<bq1>=*)\[(?s:.)*?\](?P=bq1)\]",
    "OPEN_PAREN": r"\(",
    "CLOSE_PAREN": r"\)",
    "LEGACY": r'\b\w+=[^\s"()$\\]*(?:"[^"\\]*"[^\s"()$\\]*)*|"(?:[^"\\]*(?:\\.[^"\\]*)*)*"',
    "UNQUOTED": r"(?:\\.|[^\s()#\"\\])+",
}


class TokenType(enum.Enum):
    BRACKET_COMMENT = enum.auto()
    COMMENT = enum.auto()
    UNQUOTED = enum.auto()
    QUOTED = enum.auto()
    BRACKET_QUOTE = enum.auto()
    LEGACY = enum.auto()
    OPEN_PAREN = enum.auto()
    CLOSE_PAREN = enum.auto()
    WHITESPACE = enum.auto()


@dataclasses.dataclass(frozen=True)
class Token:
    __slots__ = ("start", "stop", "type", "value")

    type: TokenType
    start: int
    stop: int
    value: str

    def __str__(self) -> str:
        return f"{self.type.name}({self.value!r})"


def tokenize(contents: str) -> Generator[Token, None, None]:
    tok_regex = "|".join(f"(?P<{n}>{v})" for n, v in TOKEN_EXPRS.items())
    last = 0
    for match in re.finditer(tok_regex, contents, re.MULTILINE):
        for typ, value in match.groupdict().items():
            if typ in TOKEN_EXPRS and value is not None:
                if match.start() != last:
                    yield Token(
                        TokenType.WHITESPACE,
                        last,
                        match.start(),
                        contents[last : match.start()],
                    )
                last = match.end()
                yield Token(TokenType[typ], match.start(), match.end(), value)


if __name__ == "__main__":
    with Path(sys.argv[1]).open(encoding="utf-8-sig") as f:
        for token in tokenize(f.read()):
            rich_print(
                "{green}{token.type.name}{red}({default}{token.value}{red})",
                token=token,
            )
