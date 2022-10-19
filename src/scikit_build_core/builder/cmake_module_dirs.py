from __future__ import annotations

import contextlib
from collections.abc import Callable, Generator
from pathlib import Path

from .._compat.importlib import Traversable, metadata, resources

__all__: list[str] = ["provide_cmake_modules"]


def __dir__() -> list[str]:
    return __all__


def get_cmake_modules_traversables(select: Callable[[str], bool]) -> list[Traversable]:
    module_dirs = metadata.entry_points(group="cmake.modules")
    return [resources.files(ep.load()) for ep in module_dirs if select(ep.name)]


@contextlib.contextmanager
def provide_cmake_modules(
    select: Callable[[str], bool] = lambda _: True
) -> Generator[list[Path], None, None]:
    with contextlib.ExitStack() as stack:
        paths = [
            stack.enter_context(resources.as_file(dir))
            for dir in get_cmake_modules_traversables(select)
        ]
        yield paths
