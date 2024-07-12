from __future__ import annotations

import dataclasses
import sys
from pathlib import Path
from typing import TYPE_CHECKING

from .._logging import rich_print
from .tokenizer import Token, TokenType, tokenize

if TYPE_CHECKING:
    from collections.abc import Generator

__all__ = ["Node", "Block", "parse"]


def __dir__() -> list[str]:
    return __all__


@dataclasses.dataclass(frozen=True)
class Node:
    __slots__ = ("name", "value", "start", "stop")

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
            if token.type != TokenType.FUNCTION:
                continue
            first_paren = token.value.index("(")
            name = token.value[:first_paren].lower()
            value = token.value[first_paren + 1 : -1]
            if name == "if":
                yield Block(
                    name, value, token.start, token.end, list(parse(tokens, "endif"))
                )
            elif name == "foreach":
                yield Block(
                    name,
                    value,
                    token.start,
                    token.end,
                    list(parse(tokens, "endforeach")),
                )
            elif name == "while":
                yield Block(
                    name, value, token.start, token.end, list(parse(tokens, "endwhile"))
                )
            elif name == "macro":
                yield Block(
                    name, value, token.start, token.end, list(parse(tokens, "endmacro"))
                )
            elif name == "function":
                yield Block(
                    name,
                    value,
                    token.start,
                    token.end,
                    list(parse(tokens, "endfunction")),
                )
            elif name == "block":
                yield Block(
                    name, value, token.start, token.end, list(parse(tokens, "endblock"))
                )
            else:
                yield Node(name, value, token.start, token.end)
            if stop and name == stop:
                break
    except StopIteration:
        pass


if __name__ == "__main__":
    with Path(sys.argv[1]).open(encoding="utf-8") as f:
        for node in parse(tokenize(f.read())):
            cnode = dataclasses.replace(
                node,
                name=f"[bold blue]{node.name}[/bold /blue]",
                value=f"[green]{node.value}[/green]",
            )
            rich_print(cnode)
