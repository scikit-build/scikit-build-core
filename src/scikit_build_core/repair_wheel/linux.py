"""
Repair Linux RPATH
"""

from __future__ import annotations

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

    def patch_linux_library_rpath(self, artifact: Path, rpaths: list[str]) -> None:
        """Patch the rpaths of a specific library."""
        # Flatten the current rpaths
        curr_rpaths = {
            path
            for dt_rpaths in elf_read_rpaths(artifact).values()
            for path in dt_rpaths
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
            if not self.path_is_in_site_packages(rpath_path):
                # If it does not point to wheel install path, just keep it
                final_rpaths.add(rpath_str)
                continue
            # Otherwise change the RPATH to point use $ORIGIN
            new_rpath = self.path_relative_site_packages(rpath_path, artifact.parent)
            new_rpath_str = f"$ORIGIN/{new_rpath}"
            final_rpaths.add(new_rpath_str)
        # Merge with all the rpaths we were given
        final_rpaths = final_rpaths.union(rpaths)
        patcher = Patchelf()
        patcher.set_rpath(artifact, ":".join(final_rpaths))

    def get_dependency_rpaths(self, target: Target, install_path: Path) -> list[str]:
        """Get the rpaths due to target link dependencies."""
        target_path = self.install_dir / install_path
        rpaths = []
        for dep_target in self.get_library_dependencies(target):
            dep_install_paths = self.get_wheel_install_paths(dep_target)
            assert len(dep_install_paths) == 1
            dep_install_path = self.install_dir / next(iter(dep_install_paths))
            rpath = self.path_relative_site_packages(dep_install_path, target_path)
            new_rpath_str = f"$ORIGIN/{rpath}"
            rpaths.append(new_rpath_str)
        return rpaths

    def get_package_rpaths(self, target: Target, install_path: Path) -> list[str]:
        """
        Get the rpaths due to external package linkage.

        Have to use the linker flags until the package targets are exposed.
        https://gitlab.kitware.com/cmake/cmake/-/issues/26755
        """
        if not target.link:
            return []
        rpaths = []
        for link_command in target.link.commandFragments:
            if link_command.role == "flags":
                if not link_command.fragment:
                    logger.debug(
                        "Skipping {target} link-flags: {flags}",
                        target=target.name,
                        flags=link_command.fragment,
                    )
                continue
            if link_command.role != "libraries":
                logger.warning(
                    "File-api link role {role} is not supported. "
                    "Target={target}, command={command}",
                    target=target.name,
                    role=link_command.role,
                    command=link_command.fragment,
                )
                continue
            # Try to parse `-Wl,-rpath` flags
            if link_command.fragment.startswith("-Wl,-rpath,"):
                # removeprefix(`-Wl,-rpath,`) but compatible with Python 3.9
                check_rpaths = link_command.fragment[len("-Wl,-rpath,") :]
                for rpath_str in check_rpaths.split(":"):
                    if not rpath_str:
                        # Skip empty rpaths. Most likely will have on at the end
                        continue
                    rpath = Path(rpath_str)
                    if not self.path_is_in_site_packages(rpath):
                        # Skip any paths that cannot be handled. We do not check for paths in
                        # the build directory, it should be covered by `get_dependency_rpaths`
                        continue
                    rpath = self.path_relative_site_packages(rpath, install_path)
                    new_rpath_str = f"$ORIGIN/{rpath}"
                    rpaths.append(new_rpath_str)
            # The remaining case should be a path
            try:
                # TODO: how to best catch if a string is a valid path?
                rpath = Path(link_command.fragment)
                if not rpath.is_absolute():
                    # Relative paths should be handled by `get_dependency_rpaths`
                    continue
                rpath = self.path_relative_site_packages(rpath, install_path)
                new_rpath_str = f"$ORIGIN/{rpath.parent}"
                rpaths.append(new_rpath_str)
            except Exception:
                logger.warning(
                    "Could not parse link-library as a path: {fragment}",
                    fragment=link_command.fragment,
                )
                continue
        return rpaths

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
            dependency_rpaths = self.get_dependency_rpaths(target, install_path)
            package_rpaths = self.get_package_rpaths(target, install_path)
            self.patch_linux_library_rpath(
                artifact=target_path / artifact.path,
                rpaths=[*dependency_rpaths, *package_rpaths],
            )
