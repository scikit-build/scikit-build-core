from __future__ import annotations

import dataclasses
import sys
from pathlib import Path
from typing import TYPE_CHECKING

from .._logging import rich_print
from .tokenizer import Token, TokenType, tokenize

if TYPE_CHECKING:
    from collections.abc import Generator

__all__ = ["Block", "Node", "parse"]


def __dir__() -> list[str]:
    return __all__


@dataclasses.dataclass(frozen=True)
class Node:
    __slots__ = ("name", "start", "stop", "value")

    name: str
    value: str
    start: int
    stop: int

    def __str__(self) -> str:
        return f"{self.name}({self.value})"


@dataclasses.dataclass(frozen=True)
class Block(Node):
    __slots__ = ("contents",)

    contents: list[Node]

    def __str__(self) -> str:
        return f"{super().__str__()} ... {len(self.contents)} children"


def parse(
    tokens: Generator[Token, None, None], stop: str = ""
) -> Generator[Node, None, None]:
    """
    Generate a stream of nodes from a stream of tokens. This currently bundles all block-like functions
    into a single `Block` node, but this could be changed to be more specific eventually if needed.
    """
    try:
        while True:
            token = next(tokens)
            if token.type != TokenType.UNQUOTED:
                continue
            name = token.value.lower()
            start = token.start
            token = next(tokens)
            if token.type == TokenType.WHITESPACE:
                token = next(tokens)
            if token.type != TokenType.OPEN_PAREN:
                msg = f"Expected open paren after {name!r}, got {token!r}"
                raise AssertionError(msg)
            count = 1
            value = ""
            while True:
                token = next(tokens)
                if token.type == TokenType.OPEN_PAREN:
                    count += 1
                elif token.type == TokenType.CLOSE_PAREN:
                    count -= 1
                    if count == 0:
                        break
                value += token.value

            if name in {"if", "foreach", "while", "macro", "function", "block"}:
                contents = list(parse(tokens, f"end{name}"))
                yield Block(name, value, start, contents[-1].stop, contents)
            else:
                yield Node(name, value, start, token.stop)
            if stop and name == stop:
                break
    except StopIteration:
        pass


if __name__ == "__main__":
    with Path(sys.argv[1]).open(encoding="utf-8-sig") as f:
        for node in parse(tokenize(f.read())):
            node_name = node.name.replace("{", "{{").replace("}", "}}")
            node_value = node.value.replace("{", "{{").replace("}", "}}")
            cnode = dataclasses.replace(
                node,
                name=f"{{bold.blue}}{node_name}{{default}}",
                value=f"{{green}}{node_value}{{default}}",
            )
            rich_print(cnode)
