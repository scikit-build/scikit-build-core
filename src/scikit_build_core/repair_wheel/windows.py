"""
Repair Windows dll path
"""

from __future__ import annotations

import dataclasses
import functools
import os.path
import textwrap
from pathlib import Path
from typing import TYPE_CHECKING, ClassVar

from .._logging import logger
from .base import WheelRepairer, _get_buildenv_platlib

if TYPE_CHECKING:
    import re

    from ..file_api.model.codemodel import Target

__all__ = ["WindowsWheelRepairer"]


def __dir__() -> list[str]:
    return __all__


@dataclasses.dataclass
class WindowsWheelRepairer(WheelRepairer):
    """
    Patch the package and top-level python module files with ``os.add_dll_directory``.
    """

    _platform = "Windows"

    PATCH_PY_FILE: ClassVar[str] = textwrap.dedent("""\
    # start scikit-build-core Windows patch
    def _skbuild_patch_dll_dir():
        import os
        import os.path

        mod_dir = os.path.abspath(os.path.dirname(__file__))
        path_to_platlib = os.path.normpath({path_to_platlib!r})
        dll_paths = {dll_paths!r}
        for path in dll_paths:
            path = os.path.normpath(path)
            path = os.path.join(mod_dir, path_to_platlib, path)
            os.add_dll_directory(path)

    _skbuild_patch_dll_dir()
    del _skbuild_patch_dll_dir
    # end scikit-build-core Windows patch
    """)
    dll_dirs: set[Path] = dataclasses.field(default_factory=set, init=False)
    """All dll paths used relative to ``platlib``."""

    @functools.cached_property
    def bundle_external(self) -> list[re.Pattern[str]]:
        if self.settings.wheel.repair.bundle_external:
            logger.warning("Bundling Windows dll files is not supported yet.")
        return []

    def try_bundle(self, external_lib: Path) -> Path | None:
        # Everything should be gated by `bundle_external` so this should not be called
        # TODO: figure out a better way to find the corresponding dll file of the linked lib file
        raise NotImplementedError

    def get_dll_path_from_lib(self, lib_path: Path) -> Path | None:
        """Guess the dll path from lib path."""
        # TODO: rework the logic of this to work with `try_bundle`
        dll_path = None
        platlib = Path(_get_buildenv_platlib())
        lib_path = lib_path.relative_to(platlib)
        # Change the `.lib` to `.dll`
        if ".dll" in (suffixes := lib_path.suffixes):
            # In some cases like msys, they use `.dll.a`, in which case we can't use `with_suffix`
            if suffixes[-2] != ".dll":
                logger.warning(
                    "Expected .dll suffix to be the penultimate extension, instead got: {lib_path}",
                    lib_path=lib_path,
                )
                return None
            # Drop the last suffix it should then be just .dll file
            dll_name = lib_path.stem
        else:
            dll_name = lib_path.with_suffix(".dll").name
        # Try to find the dll in the same package directory
        if len(lib_path.parts) > 1:
            pkg_dir = lib_path.parts[0]
            for root, _, files in os.walk(platlib / pkg_dir):
                if dll_name in files:
                    dll_path = Path(root) / dll_name
                    break
            else:
                logger.debug(
                    "Did not find the dll file under {pkg_dir}",
                    pkg_dir=pkg_dir,
                )
        if not dll_path:
            logger.debug(
                "Looking for {dll_name} in all platlib path.",
                dll_name=dll_name,
            )
            for root, _, files in os.walk(platlib):
                if dll_name in files:
                    dll_path = Path(root) / dll_name
                    break
            else:
                logger.warning(
                    "Could not find dll file {dll_name} corresponding to {lib_path}",
                    dll_name=dll_name,
                    lib_path=lib_path,
                )
                return None
        logger.debug(
            "Found dll file {dll_path}",
            dll_path=dll_path,
        )
        return self.path_relative_site_packages(dll_path)

    def get_library_dependencies(self, target: Target) -> list[Target]:
        msg = "get_library_dependencies is not generalized for Windows."
        raise NotImplementedError(msg)

    def get_dependency_dll(self, target: Target) -> list[Path]:
        """Get the dll due to target link dependencies."""
        dll_paths = []
        for dep in target.dependencies:
            dep_target = next(targ for targ in self.targets if targ.id == dep.id)
            if dep_target.type != "SHARED_LIBRARY":
                logger.debug(
                    "Skipping dependency {dep_target} of type {type}",
                    dep_target=dep_target.name,
                    type=dep_target.type,
                )
                continue
            if not dep_target.install:
                logger.warning(
                    "Dependency {dep_target} is not installed",
                    dep_target=dep_target.name,
                )
                continue
            dll_artifact = next(
                artifact.path.name
                for artifact in dep_target.artifacts
                if artifact.path.suffix == ".dll"
            )
            for install_path in self.get_wheel_install_paths(dep_target):
                dep_install_path = self.install_dir / install_path
                if (dep_install_path / dll_artifact).exists():
                    break
            else:
                logger.warning(
                    "Could not find installed {dll_artifact} location in install paths: {install_path}",
                    dll_artifact=dll_artifact,
                    install_path=[
                        dest.path for dest in dep_target.install.destinations
                    ],
                )
                continue
            dll_path = self.path_relative_site_packages(dep_install_path)
            dll_paths.append(dll_path)
        return dll_paths

    def get_package_dll(self, target: Target) -> list[Path]:
        """
        Get the dll due to external package linkage.

        Have to use the guess the dll paths until the package targets are exposed.
        https://gitlab.kitware.com/cmake/cmake/-/issues/26755
        """
        if not target.link:
            return []
        dll_paths = []
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
            # The remaining case should be a path
            try:
                # TODO: how to best catch if a string is a valid path?
                lib_path = Path(link_command.fragment)
            except Exception as exc:
                logger.warning(
                    "Could not parse link-library as a path: {fragment}\nexc = {exc}",
                    fragment=link_command.fragment,
                    exc=exc,
                )
                continue
            if not lib_path.is_absolute():
                # If the link_command is a space-separated list of libraries, this should be skipped
                logger.debug(
                    "Skipping non-absolute-path library: {fragment}",
                    fragment=link_command.fragment,
                )
                continue
            # TODO: Handle this better when revisiting `try_bundle`
            if not self.get_package_lib_path(lib_path):
                continue
            dll_path = self.get_dll_path_from_lib(lib_path)
            if not dll_path:
                continue
            dll_paths.append(dll_path.parent)
        return dll_paths

    def patch_target(self, target: Target) -> None:
        # Here we just gather all dll paths needed for each target
        if self.settings.wheel.repair.in_wheel:
            dependency_dlls = self.get_dependency_dll(target)
        else:
            dependency_dlls = []
        package_dlls = self.get_package_dll(target)

        if not package_dlls and not dependency_dlls:
            logger.warning(
                "No dll files found for target {target}",
                target=target.name,
            )
            return
        logger.debug(
            "Found dlls for target {target}:\n"
            "package_dlls={package_dlls}\n"
            "dependency_dlls={dependency_dlls}\n",
            target=target.name,
            package_dlls=package_dlls,
            dependency_dlls=dependency_dlls,
        )
        self.dll_dirs.update(package_dlls)
        self.dll_dirs.update(dependency_dlls)

    def patch_python_file(self, file: Path) -> None:
        """
        Patch python package or top-level module.

        Make sure the python files have an appropriate ``os.add_dll_directory``
        for the scripts directory.
        """
        assert self.dll_dirs
        assert all(not path.is_absolute() for path in self.dll_dirs)
        logger.debug(
            "Patching python file: {file}",
            file=file,
        )
        platlib = Path(self.wheel_dirs["platlib"])
        content = file.read_text()
        mod_dir = file.parent
        path_to_platlib = os.path.relpath(platlib, mod_dir)
        patch_script = self.PATCH_PY_FILE.format(
            path_to_platlib=path_to_platlib,
            dll_paths=[str(path) for path in self.dll_dirs],
        )
        # TODO: Account for the header comments, __future__.annotations, etc.
        with file.open("w") as f:
            f.write(f"{patch_script}\n" + content)

    def repair_wheel(self) -> None:
        super().repair_wheel()
        platlib = Path(self.wheel_dirs["platlib"])
        if not self.dll_dirs:
            logger.debug(
                "Skipping wheel repair because no site-package dlls were found."
            )
            return
        logger.debug(
            "Patching dll directories: {dll_dirs}",
            dll_dirs=self.dll_dirs,
        )
        # TODO: Not handling namespace packages with this
        for path in platlib.iterdir():
            assert isinstance(path, Path)
            if path.is_dir():
                pkg_file = path / "__init__.py"
                if not pkg_file.exists():
                    logger.debug(
                        "Ignoring non-python package: {pkg_file}",
                        pkg_file=pkg_file,
                    )
                    continue
                self.patch_python_file(pkg_file)
            elif path.suffix == ".py":
                self.patch_python_file(path)
