"""
Repair MacOS RPATH
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from .rpath import RpathWheelRepairer

if TYPE_CHECKING:
    from pathlib import Path

__all__ = ["MacOSWheelRepairer"]


def __dir__() -> list[str]:
    return __all__


class MacOSWheelRepairer(RpathWheelRepairer):
    """
    Adjust the RPATH with @loader_path.
    """

    # TODO: Tighten multi-architecture assumption.

    _platform = "Darwin"
    _origin_symbol = "@loader_path"

    def get_library_rpath(self, artifact: Path) -> list[str]:
        import lief.MachO

        rpaths = []
        fat_macho = lief.MachO.parse(artifact)
        for macho_it in range(fat_macho.size):
            macho = fat_macho.at(macho_it)
            if not macho.has_rpath:
                continue
            for macho_rpath in macho.rpaths:
                rpaths.extend(macho_rpath.path)
        return rpaths

    def patch_library_rpath(self, artifact: Path, rpaths: list[str]) -> None:
        final_rpaths = set(rpaths)
        if final_rpaths:
            import lief.MachO

            fat_macho = lief.MachO.parse(artifact)
            for macho_it in range(fat_macho.size):
                macho = fat_macho.at(macho_it)
                macho.remove(lief.MachO.LoadCommand.TYPE.RPATH)
                for rpath in final_rpaths:
                    macho_rpath = lief.MachO.RPathCommand.create(rpath)
                    macho.add(macho_rpath)
            fat_macho.write(str(artifact))
