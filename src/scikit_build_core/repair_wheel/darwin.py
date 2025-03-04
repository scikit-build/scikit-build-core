"""
Repair MacOS RPATH
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import macholib  # noqa: F401

from . import WheelRepairer

if TYPE_CHECKING:
    from ..file_api.model.codemodel import Target

__all__ = ["MacOSWheelRepairer"]


class MacOSWheelRepairer(WheelRepairer):
    """
    Adjust the RPATH with @loader_path.
    """

    _platform = "Darwin"

    def patch_target(self, target: Target) -> None:
        # TODO: Implement patching
        pass
