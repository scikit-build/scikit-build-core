"""
Repair Linux RPATH
"""

from __future__ import annotations

from typing import TYPE_CHECKING

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
        import lief.ELF

        elf = lief.ELF.parse(artifact)
        if not elf.has(lief.ELF.DynamicEntry.TAG.RUNPATH):
            # Early exit if library does not have rpaths
            return []
        elf_rpaths = elf.get(lief.ELF.DynamicEntry.TAG.RUNPATH)
        return list(elf_rpaths.paths)

    def patch_library_rpath(self, artifact: Path, rpaths: list[str]) -> None:
        final_rpaths = set(rpaths)
        if final_rpaths:
            import lief.ELF

            elf_rpaths = lief.ELF.DynamicEntryRunPath()
            for rpath in final_rpaths:
                elf_rpaths.append(rpath)
            elf = lief.ELF.parse(artifact)
            elf.remove(lief.ELF.DynamicEntry.TAG.RUNPATH)
            elf.add(elf_rpaths)
            elf.write(str(artifact))
