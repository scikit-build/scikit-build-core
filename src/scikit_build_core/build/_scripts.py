from __future__ import annotations

import contextlib
import re
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path

__all__ = ["process_script_dir"]


def __dir__() -> list[str]:
    return __all__


SHEBANG_PATTERN = re.compile(r"^#!.*(?:python|pythonw|pypy)[0-9.]*([ \t].*)?$")


def process_script_dir(script_dir: Path) -> None:
    for item in script_dir.iterdir():
        content = []
        with contextlib.suppress(UnicodeDecodeError), item.open(encoding="utf-8") as f:
            file_iter = iter(f)
            try:
                # TODO: handle empty files
                first_line = next(file_iter)
            except StopIteration:
                first_line = ""
            match = SHEBANG_PATTERN.match(first_line)
            if match:
                content = [f"#!python{match.group(1) or ''}\n", *file_iter]
        if content:
            with item.open("w", encoding="utf-8") as f:
                f.writelines(content)
