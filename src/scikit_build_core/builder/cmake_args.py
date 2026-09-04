from __future__ import annotations

from typing import NamedTuple

TYPE_CHECKING = False
if TYPE_CHECKING:
    from collections.abc import Iterator, Sequence

__all__ = ["CMakeDefine", "iter_cmake_defines"]


def __dir__() -> list[str]:
    return __all__


class CMakeDefine(NamedTuple):
    start: int
    stop: int
    name: str
    value: str


def iter_cmake_defines(args: Sequence[str]) -> Iterator[CMakeDefine]:
    """
    Yield every ``-D`` define in ``args``, in both the joined ``-DVAR=value``
    and the two-token ``-D VAR=value`` forms. An optional ``:TYPE`` is dropped
    from the name. ``args[start:stop]`` is the token span of the define.
    """
    i = 0
    while i < len(args):
        arg = args[i]
        if arg == "-D" and i + 1 < len(args):
            stop, body = i + 2, args[i + 1]
        elif arg.startswith("-D"):
            stop, body = i + 1, arg[2:]
        else:
            i += 1
            continue
        name, sep, value = body.strip().partition("=")
        if sep:
            yield CMakeDefine(i, stop, name.partition(":")[0].strip(), value)
        i = stop
