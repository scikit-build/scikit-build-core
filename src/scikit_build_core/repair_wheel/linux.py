"""
Repair Linux RPATH
"""

from __future__ import annotations

import os.path
from pathlib import Path
from typing import TYPE_CHECKING

from auditwheel.elfutils import elf_read_rpaths
from auditwheel.patcher import Patchelf

from .._logging import logger
from . import WheelRepairer

if TYPE_CHECKING:
    from ..file_api.model.codemodel import Target

__all__ = ["LinuxWheelRepairer"]


class LinuxWheelRepairer(WheelRepairer):
    """
    Adjust the RPATH with $ORIGIN.
    """

    _platform = "Linux"

    def patch_linux_library_rpath(self, lib: Path, rpaths: list[str]) -> None:
        """Patch the rpaths of a specific library."""
        # Flatten the current rpaths
        curr_rpaths = {
            path for dt_rpaths in elf_read_rpaths(lib).values() for path in dt_rpaths
        }
        final_rpaths = set()
        # Patch pre-existing rpaths
        for rpath_str in curr_rpaths:
            # If the rpath is already relative keep it
            if rpath_str.startswith("$ORIGIN"):
                final_rpaths.add(rpath_str)
                continue
            # Otherwise check if we need to patch it
            rpath_path = Path(rpath_str)
            try:
                rpath_path.relative_to(self.install_dir)
            except ValueError:
                # If it does not point to wheel install path, just keep it
                final_rpaths.add(rpath_str)
                continue
            # Otherwise change the RPATH to point use $ORIGIN
            new_rpath = os.path.relpath(rpath_str, lib.parent)
            new_rpath = f"$ORIGIN/{new_rpath}"
            final_rpaths.add(new_rpath)
        # Merge with all the rpaths we were given
        final_rpaths = final_rpaths.union(rpaths)
        patcher = Patchelf()
        patcher.set_rpath(lib, ":".join(final_rpaths))

    def patch_target(self, target: Target) -> None:
        # Get the target install paths where the $ORIGIN is calculated from
        target_install_paths = self.get_wheel_install_paths(target)
        if not target_install_paths:
            logger.debug(
                "Skip patching {target} because all install paths are outside the wheel.",
                target=target.name,
            )
            return
        if len(set(target.artifacts)) != 1:
            logger.warning(
                "Unexpected multiple artifacts for target {target}: {artifacts}",
                target=target.name,
                artifacts=[item.path for item in target.artifacts],
            )
            return
        artifact = target.artifacts[0]
        for install_path in target_install_paths:
            target_path = self.install_dir / install_path
            dependency_rpaths = []
            for dep_target in self.get_library_dependencies(target):
                dep_install_paths = self.get_wheel_install_paths(dep_target)
                assert len(dep_install_paths) == 1
                dep_path = self.install_dir / next(iter(dep_install_paths))
                rpath = os.path.relpath(dep_path, target_path)
                rpath = f"$ORIGIN/{rpath}"
                dependency_rpaths.append(rpath)
            self.patch_linux_library_rpath(
                lib=target_path / artifact.path,
                rpaths=dependency_rpaths,
            )
