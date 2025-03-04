"""
Repair MacOS RPATH
"""

from __future__ import annotations

import dataclasses
from typing import TYPE_CHECKING

from .base import WheelRepairer

if TYPE_CHECKING:
    from ..file_api.model.codemodel import Target

__all__ = ["MacOSWheelRepairer"]


def __dir__() -> list[str]:
    return __all__


@dataclasses.dataclass
class MacOSWheelRepairer(WheelRepairer):
    """
    Adjust the RPATH with @loader_path.
    """

    _platform = "Darwin"

    def patch_target(self, target: Target) -> None:
        # TODO: Implement patching
        pass
