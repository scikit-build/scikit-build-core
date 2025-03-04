"""
Repair Linux RPATH
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from . import WheelRepairer

if TYPE_CHECKING:
    from ..file_api.model.codemodel import Target

__all__ = ["LinuxWheelRepairer"]


def __dir__() -> list[str]:
    return __all__


class LinuxWheelRepairer(WheelRepairer):
    """
    Adjust the RPATH with $ORIGIN.
    """

    _platform = "Linux"

    def patch_target(self, target: Target) -> None:
        # TODO: Implement patching
        pass
