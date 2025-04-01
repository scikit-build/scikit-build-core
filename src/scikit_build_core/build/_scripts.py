from __future__ import annotations

import contextlib
import os.path
import re
from typing import TYPE_CHECKING

from .._logging import logger

if TYPE_CHECKING:
    from pathlib import Path

    from .._vendor.pyproject_metadata import StandardMetadata
    from ..builder.builder import Builder
    from ..settings.skbuild_model import ScikitBuildSettings

__all__ = ["add_dynamic_scripts", "process_script_dir"]


def __dir__() -> list[str]:
    return __all__


SHEBANG_PATTERN = re.compile(r"^#!.*(?:python|pythonw|pypy)[0-9.]*([ \t].*)?$")
SCRIPT_PATTERN = re.compile(r"^(?P<module>[\w\\.]+)(?::(?P<function>\w+))?$")


def process_script_dir(script_dir: Path) -> None:
    for item in script_dir.iterdir():
        content = []
        with contextlib.suppress(UnicodeDecodeError), item.open(encoding="utf-8") as f:
            file_iter = iter(f)
            try:
                # TODO: handle empty files
                first_line = next(file_iter)
            except StopIteration:
                first_line = ""
            match = SHEBANG_PATTERN.match(first_line)
            if match:
                content = [f"#!python{match.group(1) or ''}\n", *file_iter]
        if content:
            with item.open("w", encoding="utf-8") as f:
                f.writelines(content)


WRAPPER = """\
import os.path
import subprocess
import sys

DIR = os.path.abspath(os.path.dirname(__file__))

def {function}() -> None:
    exe_path = os.path.join(DIR, "{rel_exe_path}")
    sys.exit(subprocess.call([str(exe_path), *sys.argv[2:]]))

"""

WRAPPER_MODULE_EXTRA = """\

if __name__ == "__main__":
    {function}()

"""


def add_dynamic_scripts(
    *,
    metadata: StandardMetadata,
    settings: ScikitBuildSettings,
    builder: Builder | None,
    wheel_dirs: dict[str, Path],
    install_dir: Path,
    create_files: bool = False,
) -> None:
    """
    Add and create the dynamic ``project.scripts`` from the ``tool.scikit-build.scripts``.
    """
    targetlib = "platlib" if "platlib" in wheel_dirs else "purelib"
    targetlib_dir = wheel_dirs[targetlib]
    if create_files and builder:
        if not (file_api := builder.config.file_api):
            logger.warning("CMake file-api was not generated.")
            return
        build_type = builder.config.build_type
        assert file_api.reply.codemodel_v2
        configuration = next(
            conf
            for conf in file_api.reply.codemodel_v2.configurations
            if conf.name == build_type
        )
    else:
        configuration = None
    for script in settings.scripts:
        if script.target is None:
            # Early exit if we do not need to create a wrapper
            metadata.scripts[script.name] = script.path
            continue
        python_file_match = SCRIPT_PATTERN.match(script.path)
        if not python_file_match:
            logger.warning(
                "scripts.{script}.path is not a valid entrypoint",
                script=script.name,
            )
            continue
        function = python_file_match.group("function") or "main"
        pkg_mod = python_file_match.group("module").rsplit(".", maxsplit=1)
        # Modify the metadata early and exit if we do not need to create the wrapper content
        # Make sure to include the default function if it was not provided
        metadata.scripts[script.name] = f"{'.'.join(pkg_mod)}:{function}"
        if not create_files or not configuration:
            continue
        # Create the file contents from here on
        # Try to find the python file
        if len(pkg_mod) == 1:
            pkg = None
            mod = pkg_mod[0]
        else:
            pkg, mod = pkg_mod

        pkg_dir = targetlib_dir
        if pkg:
            # Make sure all intermediate package files are populated
            for pkg_part in pkg.split("."):
                pkg_dir = pkg_dir / pkg_part
                pkg_file = pkg_dir / "__init__.py"
                pkg_dir.mkdir(exist_ok=True)
                pkg_file.touch(exist_ok=True)
        # Check if module is a module or a package
        if (pkg_dir / mod).is_dir():
            mod_file = pkg_dir / mod / "__init__.py"
        else:
            mod_file = pkg_dir / f"{mod}.py"
        if mod_file.exists():
            logger.warning(
                "Wrapper file already exists: {mod_file}",
                mod_file=mod_file,
            )
            continue
        # Get the requested target
        for target in configuration.targets:
            if target.type != "EXECUTABLE":
                continue
            if target.name == script.target:
                break
        else:
            logger.warning(
                "Could not find target: {target}",
                target=script.target,
            )
            continue
        # Find the installed artifact
        if len(target.artifacts) > 1:
            logger.warning(
                "Multiple target artifacts is not supported: {artifacts}",
                artifacts=target.artifacts,
            )
            continue
        if not target.install:
            logger.warning(
                "Target is not installed: {target}",
                target=target.name,
            )
            continue
        target_artifact = target.artifacts[0].path
        for dest in target.install.destinations:
            install_path = dest.path
            if install_path.is_absolute():
                try:
                    install_path = install_path.relative_to(targetlib_dir)
                except ValueError:
                    continue
            else:
                install_path = install_dir / install_path
            install_artifact = targetlib_dir / install_path / target_artifact.name
            if not install_artifact.exists():
                logger.warning(
                    "Did not find installed executable: {artifact}",
                    artifact=install_artifact,
                )
                continue
            break
        else:
            logger.warning(
                "Did not find installed files for target: {target}",
                target=target.name,
            )
            continue
        # Generate the content
        content = WRAPPER.format(
            function=function,
            rel_exe_path=os.path.relpath(install_artifact, mod_file.parent),
        )
        if script.as_module:
            content += WRAPPER_MODULE_EXTRA.format(function=function)
        with mod_file.open("w", encoding="utf-8") as f:
            f.write(content)
