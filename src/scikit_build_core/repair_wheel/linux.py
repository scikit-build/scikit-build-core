"""
Repair Linux RPATH
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from auditwheel.elfutils import elf_read_rpaths
from auditwheel.patcher import Patchelf

from .rpath import RpathWheelRepairer

if TYPE_CHECKING:
    from pathlib import Path

__all__ = ["LinuxWheelRepairer"]


def __dir__() -> list[str]:
    return __all__


class LinuxWheelRepairer(RpathWheelRepairer):
    """
    Adjust the RPATH with $ORIGIN.
    """

    _platform = "Linux"
    _origin_symbol = "$ORIGIN"

    def get_library_rpath(self, artifact: Path) -> list[str]:
        return [
            path
            for dt_rpaths in elf_read_rpaths(artifact).values()
            for path in dt_rpaths
        ]

    def patch_library_rpath(self, artifact: Path, rpaths: list[str]) -> None:
        final_rpaths = set(rpaths)
        if final_rpaths:
            patcher = Patchelf()
            patcher.set_rpath(artifact, ":".join(final_rpaths))
