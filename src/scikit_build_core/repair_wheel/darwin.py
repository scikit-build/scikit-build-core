"""
Repair MacOS RPATH
"""

from __future__ import annotations

import dataclasses
from typing import TYPE_CHECKING

from .._logging import logger
from .rpath import RpathWheelRepairer

if TYPE_CHECKING:
    from pathlib import Path

__all__ = ["MacOSWheelRepairer"]


def __dir__() -> list[str]:
    return __all__


@dataclasses.dataclass
class MacOSWheelRepairer(RpathWheelRepairer):
    """
    Adjust the RPATH with @loader_path.
    """

    # TODO: Tighten multi-architecture assumption.

    _platform = "Darwin"
    _origin_symbol = "@loader_path"

    def get_library_rpath(self, artifact: Path) -> list[str]:
        from delocate.tools import _get_rpaths

        arch_rpaths = _get_rpaths(artifact)
        if len(arch_rpaths) > 1:
            logger.warning("Multiple architecture rpath parsing not implemented")
        return [path for arch in arch_rpaths for path in arch_rpaths[arch]]

    def patch_library_rpath(self, artifact: Path, rpaths: list[str]) -> None:
        from delocate.tools import _delete_rpaths, add_rpath

        original_rpaths = self.get_library_rpath(artifact)
        _delete_rpaths(str(artifact), set(original_rpaths))
        final_rpaths = set(rpaths)
        for rpath in final_rpaths:
            add_rpath(str(artifact), rpath)
