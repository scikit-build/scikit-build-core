"""
Base classes for the wheel repairers.
"""

from __future__ import annotations

import dataclasses
import functools
import os
import platform
import sysconfig
import typing
from abc import ABC, abstractmethod
from pathlib import Path
from typing import ClassVar, Final

from .._logging import logger

if typing.TYPE_CHECKING:
    from ..build._wheelfile import WheelWriter
    from ..builder.builder import Builder
    from ..file_api.model.codemodel import Configuration, Target


__all__ = [
    "WheelRepairer",
]


def __dir__() -> list[str]:
    return __all__


DIR = Path(__file__).parent.resolve()


@functools.lru_cache(1)
def _get_buildenv_platlib() -> str:
    # Normally we could `sysconfig.get_path("platlib")` directly, but pip fake-venv breaks it
    platlib_path = sysconfig.get_path("platlib")
    purelib_path = sysconfig.get_path("purelib")
    real_purelib_path = DIR.parent.parent
    if real_purelib_path.samefile(purelib_path):
        # Here is the normal state if we are in a real venv
        return str(Path(platlib_path).resolve())
    # Otherwise we need to trick it to giving us the real path
    data_path = sysconfig.get_path("data")
    platlib_relative_path = Path(platlib_path).relative_to(data_path)
    purelib_relative_path = Path(purelib_path).relative_to(data_path)

    # removesuffix(purelib_relative_path)
    if str(real_purelib_path).rfind(str(purelib_relative_path)) == -1:
        logger.warning(
            "Could not figure out the true build-env path:\n"
            "sysconfig_purelib = {sysconfig_purelib}\n"
            "scikit-build-core_purelib = {real_purelib}\n",
            sysconfig_purelib=purelib_path,
            real_purelib=real_purelib_path,
        )
        return platlib_path
    real_root = str(real_purelib_path)[: -len(str(purelib_relative_path))]
    real_platlib_path = str(Path(real_root) / platlib_relative_path)
    # Yet another dirty trick necessary
    real_platlib_path = real_platlib_path.replace(
        os.path.normpath("/overlay/"),
        os.path.normpath("/normal/"),
    )
    logger.debug("Calculated real_platlib_path = {}", real_platlib_path)
    return str(real_platlib_path)


@dataclasses.dataclass
class WheelRepairer(ABC):
    """Abstract wheel repairer."""

    wheel: WheelWriter
    """The current wheel creator."""
    builder: Builder
    """CMake builder used."""
    install_dir: Path
    """Wheel install directory of the CMake project."""
    wheel_dirs: dict[str, Path]
    """Wheel packaging directories."""
    _platform_repairers: ClassVar[dict[str, type[WheelRepairer]]] = {}
    """Dictionary of platform specific repairers"""
    _platform: ClassVar[str | None] = None
    """The ``platform.system()`` corresponding to the current repairer."""
    _initialized: Final[bool] = False
    """Whether all ``WheelRepairer`` have been initialized."""
    _filter_targets: ClassVar[bool] = True
    """Whether to filter the targets before calling ``patch_target``."""

    def __init_subclass__(cls) -> None:
        if cls._platform:
            WheelRepairer._platform_repairers[cls._platform] = cls

    @functools.cached_property
    def configuration(self) -> Configuration:
        """Current file-api configuration."""
        assert self.builder.config.file_api
        reply = self.builder.config.file_api.reply
        assert reply.codemodel_v2
        return next(
            conf
            for conf in reply.codemodel_v2.configurations
            if conf.name == self.builder.config.build_type
        )

    @property
    def targets(self) -> list[Target]:
        """All targets found from file-api."""
        return self.configuration.targets

    def path_relative_site_packages(
        self,
        path: Path,
        relative_to: Path | None = None,
    ) -> Path:
        """
        Transform an absolute path to a relative one in the final site-packages.

        It accounts for the temporary wheel install directory and the current build environment
        (isolated or not).

        If ``relative_to`` is not passed, the root path is the ``platlib`` wheel path. If it is
        a relative path, it is considered as relative to ``install-dir``.

        :raises ValueError: if ``path`` does not belong to the current site-packages
        """
        assert path.is_absolute(), "Path must be absolute"
        if relative_to is None:
            relative_to = self.wheel_dirs["platlib"]
        if not relative_to.is_absolute():
            relative_to = self.install_dir / relative_to
        # Make sure relative_to is relative to platlib path, otherwise throw the ValueError
        relative_to.relative_to(self.wheel_dirs["platlib"])

        try:
            # Try to get the relative path in the wheel install platlib
            path.relative_to(self.wheel_dirs["platlib"])
        except ValueError:
            # Otherwise check if the path is relative to build environment
            path = path.relative_to(_get_buildenv_platlib())
            # Mock the path to be in the wheel install platlib
            path = self.wheel_dirs["platlib"] / path
        return Path(os.path.relpath(path, relative_to))

    def path_is_in_site_packages(self, path: Path) -> bool:
        """Check if a path belongs to the current site-packages."""
        try:
            self.path_relative_site_packages(path)
        except ValueError:
            return False
        return True

    def get_wheel_install_paths(self, target: Target) -> set[Path]:
        """Get a target's install paths that belong to the wheel."""
        if not target.install:
            return set()
        install_paths = []
        for dest in target.install.destinations:
            path = dest.path
            if path.is_absolute():
                try:
                    path = path.relative_to(self.install_dir)
                except ValueError:
                    continue
            install_paths.append(path)
        return set(install_paths)

    def get_library_dependencies(self, target: Target) -> list[Target]:
        """Get a target's library dependencies that need to be patched."""
        dependencies = []
        for dep in target.dependencies:
            dep_target = next(targ for targ in self.targets if targ.id == dep.id)
            if dep_target.type == "EXECUTABLE":
                logger.warning("Handling executable dependencies not supported yet.")
                continue
            if dep_target.type != "SHARED_LIBRARY":
                continue
            dep_install_paths = self.get_wheel_install_paths(dep_target)
            if not dep_install_paths:
                logger.warning(
                    "Cannot patch dependency {dep} of target {target} because "
                    "the dependency is not installed in the wheel",
                    dep=dep_target.name,
                    target=target.name,
                )
                continue
            if len(dep_install_paths) > 1:
                logger.warning(
                    "Cannot patch dependency {dep} of target {target} because "
                    "the dependency is installed in multiple locations on the wheel",
                    dep=dep_target.name,
                    target=target.name,
                )
                continue
            dependencies.append(dep_target)
        return dependencies

    def repair_wheel(self) -> None:
        """Repair the current wheel."""
        for target in self.targets:
            if self._filter_targets:
                if target.type == "STATIC_LIBRARY":
                    logger.debug(
                        "Handling static library {target} not supported yet.",
                        target=target.name,
                    )
                    continue
                if target.type not in (
                    "SHARED_LIBRARY",
                    "MODULE_LIBRARY",
                    "EXECUTABLE",
                ):
                    continue
                if not target.install:
                    logger.debug(
                        "Skip patching {target} because it is not being installed.",
                        target=target.name,
                    )
                    continue
            self.patch_target(target)

    @abstractmethod
    def patch_target(self, target: Target) -> None:
        """Patch a specific target"""

    @classmethod
    def get_wheel_repairer(
        cls,
        wheel: WheelWriter,
        builder: Builder,
        install_dir: Path,
        wheel_dirs: dict[str, Path],
    ) -> WheelRepairer:
        """Construct the platform specific wheel repairer"""
        if "platlib" not in wheel_dirs:
            # This should only happen if the user explicitly disabled platlib
            logger.warning(
                "Wheel repairer is implemented only if `wheel.platlib` is True."
            )
            return NoopWheelRepairer(
                wheel=wheel,
                builder=builder,
                install_dir=install_dir,
                wheel_dirs=wheel_dirs,
            )

        if not (
            repairer_cls := WheelRepairer._platform_repairers.get(platform.system())
        ):
            return NoopWheelRepairer(
                wheel=wheel,
                builder=builder,
                install_dir=install_dir,
                wheel_dirs=wheel_dirs,
            )
        return repairer_cls(
            wheel=wheel,
            builder=builder,
            install_dir=install_dir,
            wheel_dirs=wheel_dirs,
        )


class NoopWheelRepairer(WheelRepairer):
    """Dummy wheel repairer that just shows a warning."""

    def repair_wheel(self) -> None:
        # Do nothing
        logger.warning("Unknown platform {}. Not doing any repair.", platform.system())

    def patch_target(self, target: Target) -> None:
        pass
