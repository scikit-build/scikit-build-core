"""
Repair Windows dll path
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pefile  # noqa: F401

from . import WheelRepairer

if TYPE_CHECKING:
    from ..file_api.model.codemodel import Target

__all__ = ["WindowsWheelRepairer"]


class WindowsWheelRepairer(WheelRepairer):
    """
    Do some windows specific magic.
    """

    _platform = "Windows"

    def patch_target(self, target: Target) -> None:
        # TODO: Implement patching
        pass
