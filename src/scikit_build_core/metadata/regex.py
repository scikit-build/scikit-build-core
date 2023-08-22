from __future__ import annotations

import re
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import Mapping

__all__ = ["dynamic_metadata"]


def __dir__() -> list[str]:
    return __all__


def dynamic_metadata(
    field: str,
    settings: Mapping[str, Any],
) -> str:
    # Input validation
    if field not in {"version", "description", "requires-python"}:
        msg = "Only string fields supported by this plugin"
        raise RuntimeError(msg)
    if settings.keys() > {"input", "regex"}:
        msg = "Only 'input' and 'regex' settings allowed by this plugin"
        raise RuntimeError(msg)
    if "input" not in settings:
        msg = "Must contain the 'input' setting to perform a regex on"
        raise RuntimeError(msg)
    if field != "version" and "regex" not in settings:
        msg = "Must contain the 'regex' setting if not getting version"
        raise RuntimeError(msg)
    if not all(isinstance(x, str) for x in settings.values()):
        msg = "Must set 'input' and/or 'regex' to strings"
        raise RuntimeError(msg)

    input_filename = settings["input"]
    regex = settings.get(
        "regex", r'(?i)^(__version__|VERSION) *= *([\'"])v?(?P<value>.+?)\2'
    )

    with Path(input_filename).open(encoding="utf-8") as f:
        match = re.search(regex, f.read(), re.MULTILINE)

    if not match:
        msg = f"Couldn't find {regex!r} in {input_filename}"
        raise RuntimeError(msg)

    return match.group("value")
