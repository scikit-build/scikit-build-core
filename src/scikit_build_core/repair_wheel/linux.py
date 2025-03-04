"""
Repair Linux RPATH
"""

from __future__ import annotations

import dataclasses
from typing import TYPE_CHECKING

from .base import WheelRepairer

if TYPE_CHECKING:
    from ..file_api.model.codemodel import Target

__all__ = ["LinuxWheelRepairer"]


def __dir__() -> list[str]:
    return __all__


@dataclasses.dataclass
class LinuxWheelRepairer(WheelRepairer):
    """
    Adjust the RPATH with $ORIGIN.
    """

    _platform = "Linux"

    def patch_target(self, target: Target) -> None:
        # TODO: Implement patching
        pass
