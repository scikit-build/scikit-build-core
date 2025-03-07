"""
Repair wheel
"""

from __future__ import annotations

import dataclasses
import functools
import platform
from abc import ABC, abstractmethod
from importlib import import_module
from typing import TYPE_CHECKING, ClassVar, Final

from .._logging import logger

if TYPE_CHECKING:
    from pathlib import Path

    from ..build._wheelfile import WheelWriter
    from ..builder.builder import Builder
    from ..file_api.model.codemodel import Configuration, Target


__all__ = [
    "WheelRepairer",
]


@dataclasses.dataclass()
class WheelRepairer(ABC):
    """Abstract wheel repairer."""

    wheel: WheelWriter
    """The current wheel creator."""
    builder: Builder
    """CMake builder used."""
    install_dir: Path
    """Wheel install directory."""
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
    ) -> WheelRepairer:
        """Construct the platform specific wheel repairer"""
        WheelRepairer.initialize()
        if not (
            repairer_cls := WheelRepairer._platform_repairers.get(platform.system())
        ):
            return NoopWheelRepairer(
                wheel=wheel,
                builder=builder,
                install_dir=install_dir,
            )
        return repairer_cls(
            wheel=wheel,
            builder=builder,
            install_dir=install_dir,
        )

    @classmethod
    def initialize(cls) -> None:
        """Get all known wheel repairers."""
        if cls._initialized:
            return
        # TODO: Allow for other wheel repairers defined as entry-points
        try:
            if (platform_system := platform.system().lower()) in (
                "linux",
                "darwin",
                "windows",
            ):
                import_module(f".{platform_system}", package=__name__)
        except ImportError:
            logger.error("Could not load the platform specific wheel repairer.")
            raise


class NoopWheelRepairer(WheelRepairer):
    """Dummy wheel repairer that just shows a warning."""

    def repair_wheel(self) -> None:
        # Do nothing
        logger.warning("Unknown platform {}. Not doing any repair.", platform.system())

    def patch_target(self, target: Target) -> None:
        pass
