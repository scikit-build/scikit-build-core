"""
Repair RPATH systems
"""

from __future__ import annotations

import dataclasses
import shlex
from abc import ABC, abstractmethod
from pathlib import Path
from typing import TYPE_CHECKING, ClassVar

from .._logging import logger
from .base import WheelRepairer

if TYPE_CHECKING:
    from ..file_api.model.codemodel import Target

__all__ = ["RpathWheelRepairer"]


def __dir__() -> list[str]:
    return __all__


@dataclasses.dataclass
class RpathWheelRepairer(WheelRepairer, ABC):
    """
    Adjust the RPATH with an equivalent $ORIGIN/@loader_path.
    """

    _origin_symbol: ClassVar[str]
    """The equivalent symbol for the $ORIGIN/@loader_path in the RPATH."""

    @abstractmethod
    def get_library_rpath(self, artifact: Path) -> list[str]:
        """Get the current rpaths."""

    @abstractmethod
    def patch_library_rpath(self, artifact: Path, rpaths: list[str]) -> None:
        """Patch the rpaths of a specific library."""

    def get_dependency_rpaths(self, target: Target, install_path: Path) -> list[str]:
        """Get the rpaths due to target link dependencies."""
        target_path = self.install_dir / install_path
        rpaths = []
        for dep_target in self.get_library_dependencies(target):
            dep_install_paths = self.get_wheel_install_paths(dep_target)
            assert len(dep_install_paths) == 1
            dep_install_path = self.install_dir / next(iter(dep_install_paths))
            rpath = self.path_relative_site_packages(dep_install_path, target_path)
            new_rpath_str = f"{self._origin_symbol}/{rpath}"
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
        assert target.link.commandFragments is not None
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
            # TODO: These should be abstracted somehow?
            # CMake 3.15 didn't seem to space-separate the flags
            for link_part in shlex.split(link_command.fragment):
                # Try to parse `-Wl,-rpath` flags
                if link_part.startswith("-Wl,-rpath,"):
                    # removeprefix(`-Wl,-rpath,`) but compatible with Python 3.9
                    check_rpaths = link_part[len("-Wl,-rpath,") :]
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
                        new_rpath_str = f"{self._origin_symbol}/{rpath}"
                        rpaths.append(new_rpath_str)
                    continue
                # The remaining case should be a path
                try:
                    # TODO: how to best catch if a string is a valid path?
                    rpath = Path(link_part)
                    if not rpath.is_absolute():
                        # Relative paths should be handled by `get_dependency_rpaths`
                        continue
                    rpath = self.path_relative_site_packages(rpath, install_path)
                    new_rpath_str = f"{self._origin_symbol}/{rpath.parent}"
                    rpaths.append(new_rpath_str)
                except Exception as exc:
                    logger.warning(
                        "Could not parse link-library as a path: {fragment}\nexc = {exc}",
                        fragment=link_command.fragment,
                        exc=exc,
                    )
                    continue
        return rpaths

    def get_existing_rpaths(self, artifact: Path) -> list[str]:
        """
        Get the rpaths that are already present in the artifact.

        Keep any rpaths that contain ``_origin_symbol``, or are outside the site_packages.
        Convert the paths that point to site_packages to contain ``_origin_symbol``
        """
        patched_rpaths = []
        for rpath_str in self.get_library_rpath(artifact):
            # If the rpath is already relative keep it
            # TODO: maybe abstract this to include other symbols to skip?
            if rpath_str.startswith(self._origin_symbol):
                patched_rpaths.append(rpath_str)
                continue
            # Otherwise check if we need to patch it
            rpath_path = Path(rpath_str)
            if not self.path_is_in_site_packages(rpath_path):
                # If it does not point to wheel install path, just keep it
                patched_rpaths.append(rpath_str)
                continue
            # Otherwise change the RPATH to point use $ORIGIN
            new_rpath = self.path_relative_site_packages(rpath_path, artifact.parent)
            new_rpath_str = f"{self._origin_symbol}/{new_rpath}"
            patched_rpaths.append(new_rpath_str)
        return patched_rpaths

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
            artifact_path = target_path / artifact.path.name
            dependency_rpaths = self.get_dependency_rpaths(target, install_path)
            package_rpaths = self.get_package_rpaths(target, install_path)
            existing_rpaths = self.get_existing_rpaths(artifact_path)
            logger.debug(
                "Patching rpaths for artifact {artifact}\n"
                "existing={existing_rpaths}\n"
                "dependency={dependency_rpaths}\n"
                "package={package_rpaths}\n",
                artifact=artifact_path,
                existing_rpaths=existing_rpaths,
                dependency_rpaths=dependency_rpaths,
                package_rpaths=package_rpaths,
            )
            self.patch_library_rpath(
                artifact=artifact_path,
                rpaths=[*existing_rpaths, *dependency_rpaths, *package_rpaths],
            )
