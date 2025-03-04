"""
Repair Windows dll path
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from . import WheelRepairer

if TYPE_CHECKING:
    from ..file_api.model.codemodel import Target

__all__ = ["WindowsWheelRepairer"]


def __dir__() -> list[str]:
    return __all__


class WindowsWheelRepairer(WheelRepairer):
    """
    Do some windows specific magic.
    """

    _platform = "Windows"

    def patch_target(self, target: Target) -> None:
        # TODO: Implement patching
        pass
