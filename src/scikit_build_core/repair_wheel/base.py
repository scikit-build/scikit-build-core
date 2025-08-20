"""
Base classes for the wheel repairers.
"""

from __future__ import annotations

import dataclasses
import functools
import os
import platform
import re
import shutil
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
    from ..settings.skbuild_model import ScikitBuildSettings


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

    name: str
    """Normalized project name."""
    settings: ScikitBuildSettings
    """Pyproject settings."""
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
    def bundled_libs_path(self) -> Path:
        """Staging path for the bundled library directory."""
        return Path(self.wheel_dirs["platlib"]) / f"{self.name}.libs"

    @functools.cached_property
    def bundle_external(self) -> list[re.Pattern[str]]:
        """List of compiled regex patterns of the library files to bundle."""
        patterns = []
        for pattern_str in self.settings.wheel.repair.bundle_external:
            try:
                pattern = re.compile(pattern_str)
            except re.error as exc:
                logger.warning(
                    'Skipping "{pattern}" as an invalid pattern',
                    pattern=pattern_str,
                )
                logger.debug(str(exc))
                continue
            patterns.append(pattern)
        return patterns

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

    def try_bundle(self, external_lib: Path) -> Path | None:
        """
        Try to bundle an external library file.

        :param external_lib: path to actual external library to bundle
        :returns: ``None`` if the library is not bundled, otherwise the path
          to the bundled file
        """
        assert external_lib.is_absolute()
        if not external_lib.exists():
            logger.warning(
                "External library file does not exist: {external_lib}",
                external_lib=external_lib,
            )
            return None
        if external_lib.is_dir():
            logger.debug(
                "Skip bundling directory: {external_lib}",
                external_lib=external_lib,
            )
            return None
        libname = external_lib.name
        bundled_lib = self.bundled_libs_path / libname
        if bundled_lib.exists():
            # If we have already bundled the library no need to do it again
            return bundled_lib
        for pattern in self.bundle_external:
            if pattern.match(libname):
                logger.debug(
                    'Bundling library matching "{pattern}": {external_lib}',
                    external_lib=external_lib,
                    pattern=pattern.pattern,
                )
                shutil.copy(external_lib, bundled_lib)
                return bundled_lib
        logger.debug(
            "Skip bundling: {external_lib}",
            external_lib=external_lib,
        )
        return None

    def get_package_lib_path(
        self, original_lib: Path, relative_to: Path | None = None
    ) -> Path | None:
        """
        Get the file path of a library to be used.

        This checks for the settings in ``settings.wheel.repair`` returning either:
         - If the dependency should be skipped: ``None``
         - If ``original_lib`` is a library in another wheel: a relative path to the original library file
         - If ``original_lib`` is a library to be bundled: a relative path to the bundled library file

        The relative paths are relative to ``relative_to`` or the ``platlib`` wheel path if not passed.
        """
        if not original_lib.is_absolute() or not original_lib.exists():
            logger.debug(
                "Could not handle {original_lib} because it is either relative or does not exist.",
                original_lib=original_lib,
            )
            return None
        if self.path_is_in_site_packages(original_lib):
            # The other library is in another wheel
            if not self.settings.wheel.repair.cross_wheel:
                logger.debug(
                    "Skipping {original_lib} because it is in another wheel.",
                    original_lib=original_lib,
                )
                return None
            final_lib = original_lib
        # Otherwise, check if we need to bundle the external library
        elif not self.bundle_external or not (
            final_lib := self.try_bundle(original_lib)  # type: ignore[assignment]
        ):
            logger.debug(
                "Skipping {original_lib} because it is not being bundled.",
                original_lib=original_lib,
            )
            return None
        return self.path_relative_site_packages(final_lib, relative_to=relative_to)

    def repair_wheel(self) -> None:
        """Repair the current wheel."""
        if self.bundle_external:
            self.bundled_libs_path.mkdir(exist_ok=True)

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
        name: str,
        settings: ScikitBuildSettings,
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
                name=name,
                settings=settings,
                wheel=wheel,
                builder=builder,
                install_dir=install_dir,
                wheel_dirs=wheel_dirs,
            )

        if not (
            repairer_cls := WheelRepairer._platform_repairers.get(platform.system())
        ):
            return NoopWheelRepairer(
                name=name,
                settings=settings,
                wheel=wheel,
                builder=builder,
                install_dir=install_dir,
                wheel_dirs=wheel_dirs,
            )
        return repairer_cls(
            name=name,
            settings=settings,
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
