from __future__ import annotations

import sys
from pathlib import Path

from .. import __version__
from .._logging import rich_print
from ..program_search import info_print as ip_program_search
from .get_requires import GetRequires
from .sysconfig import info_print as ip_sysconfig
from .wheel_tag import WheelTag

__all__ = ["main"]


def __dir__() -> list[str]:
    return __all__


def main() -> None:
    rich_print(
        f"{{bold}}Scikit-build-core {__version__}{{normal}} on Python {sys.version}"
    )

    ip_sysconfig(color="green")

    rich_print(f"{{bold.blue}}Default Wheel Tag:{{normal}} {WheelTag.compute_best([])}")
    rich_print(
        "{blue} - Note: use {bold}python -m scikit_build_core.builder.wheel_tag -h{normal} for further options"
    )

    if Path("pyproject.toml").is_file():
        req = GetRequires()
        all_req = [*req.cmake(), *req.ninja(), *req.dynamic_metadata()]
        rich_print(f"{{bold.red}}Get Requires:{{normal}} {all_req!r}")

    ip_program_search(color="magenta")


if __name__ == "__main__":
    main()
