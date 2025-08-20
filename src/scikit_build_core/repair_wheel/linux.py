"""
Repair Linux RPATH
"""

from __future__ import annotations

import dataclasses
from typing import TYPE_CHECKING

from .._shutil import Run
from .rpath import RpathWheelRepairer

if TYPE_CHECKING:
    from pathlib import Path

__all__ = ["LinuxWheelRepairer"]


def __dir__() -> list[str]:
    return __all__


@dataclasses.dataclass
class LinuxWheelRepairer(RpathWheelRepairer):
    """
    Adjust the RPATH with $ORIGIN.
    """

    _platform = "Linux"
    _origin_symbol = "$ORIGIN"

    def get_library_rpath(self, artifact: Path) -> list[str]:
        from auditwheel.elfutils import elf_read_rpaths

        return [
            path
            for dt_rpaths in elf_read_rpaths(artifact).values()
            for path in dt_rpaths
        ]

    def patch_library_rpath(self, artifact: Path, rpaths: list[str]) -> None:
        final_rpaths = set(rpaths)
        if final_rpaths:
            run = Run()
            run.live("patchelf", "--remove-rpath", artifact)
            run.live("patchelf", "--set-rpath", ":".join(final_rpaths), artifact)
