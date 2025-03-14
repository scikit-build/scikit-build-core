"""
Repair Windows dll path
"""

from __future__ import annotations

import shutil
import textwrap
from pathlib import Path
from typing import TYPE_CHECKING, ClassVar

from .._logging import logger
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

    # TODO: Currently this installs the dll libraries in the scripts folder
    #  Maybe it's better to point them to the original paths instead.

    _platform = "Windows"

    PATCH_PY_FILE: ClassVar[str] = textwrap.dedent("""\
    # start scikit-build-core Windows patch
    def _skbuild_patch_dll_dir():
        import os
        import sysconfig

        os.add_dll_directory(sysconfig.get_path("scripts"))

    _skbuild_patch_dll_dir()
    del _skbuild_patch_dll_dir
    # end scikit-build-core Windows patch
    """)

    def patch_target(self, target: Target) -> None:
        if target.type == "SHARED_LIBRARY":
            # Copy the dll files to the script install path
            # TODO: Actually this would be easier using the `installers`,
            #  but that is CMake version dependent
            dll_artifact = next(
                artifact.path.name
                for artifact in target.artifacts
                if artifact.path.suffix == ".dll"
            )
            # Loop over all install paths, until we get to RUNTIME destination
            for install_path in self.get_wheel_install_paths(target):
                dll_file = self.install_dir / install_path / dll_artifact
                if not dll_file.exists():
                    continue
                # Do the copy
                shutil.copy(dll_file, self.wheel_dirs["scripts"])
                # We only need to copy the dll once
                break
            else:
                logger.warning(
                    "Could not find {dll_artifact} to copy",
                    dll_artifact=dll_artifact,
                )

    def patch_python_file(self, file: Path) -> None:
        """
        Patch python package or top-level module.

        Make sure the python files have an appropriate ``os.add_dll_directory``
        for the scripts directory.
        """
        logger.debug(
            "Patching python file: {file}",
            file=file,
        )
        # TODO: Account for the header comments, __future__.annotations, etc.
        content = file.read_text()
        with file.open("w") as f:
            f.write(f"{self.PATCH_PY_FILE}\n" + content)

    def repair_wheel(self) -> None:
        super().repair_wheel()
        platlib = Path(self.wheel_dirs["platlib"])
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
