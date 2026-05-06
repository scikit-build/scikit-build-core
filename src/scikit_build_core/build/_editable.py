from __future__ import annotations

import os
import typing
from collections.abc import Mapping
from pathlib import Path

from ..resources import resources
from ._pathutil import (
    is_valid_module,
    path_to_module,
    scantree,
)

if typing.TYPE_CHECKING:
    from collections.abc import Iterable, Sequence

    from ..settings.skbuild_model import ScikitBuildSettings

__all__ = [
    "editable_inplace_files",
    "editable_redirect",
    "editable_redirect_files",
    "get_packages",
    "libdir_to_installed",
    "mapping_to_modules",
]


def __dir__() -> list[str]:
    return __all__


def editable_redirect(
    *,
    modules: dict[str, str],
    installed: dict[str, str],
    reload_dir: Path | None,
    rebuild: bool,
    verbose: bool,
    build_options: Sequence[str],
    install_options: Sequence[str],
    install_dir: str,
) -> str:
    """
    Prepare the contents of the _editable_redirect.py file.
    """

    editable_py = resources / "_editable_redirect.py"
    editable_txt: str = editable_py.read_text(encoding="utf-8")

    arguments = (
        modules,
        installed,
        os.fspath(reload_dir) if reload_dir else None,
        rebuild,
        verbose,
        build_options,
        install_options,
        install_dir,
    )
    arguments_str = ", ".join(repr(x) for x in arguments)
    editable_txt += f"\n\ninstall({arguments_str})\n"
    return editable_txt


def editable_redirect_files(
    *,
    build_options: Sequence[str] = (),
    install_options: Sequence[str] = (),
    libdir: Path,
    mapping: dict[str, str],
    name: str,
    packages: Iterable[str],
    reload_dir: Path | None,
    settings: ScikitBuildSettings,
) -> dict[str, bytes]:
    modules = mapping_to_modules(mapping, libdir)
    installed = libdir_to_installed(libdir)
    if settings.wheel.install_dir.startswith("/"):
        msg = "Editable installs cannot rebuild an absolute wheel.install-dir. Use an override to change if needed."
        raise AssertionError(msg)
    editable_txt = editable_redirect(
        modules=modules,
        installed=installed,
        reload_dir=reload_dir,
        rebuild=settings.editable.rebuild,
        verbose=settings.editable.verbose,
        build_options=build_options,
        install_options=install_options,
        install_dir=settings.wheel.install_dir,
    )
    package_paths = tuple(packages)
    pth_import_paths = "\n".join([f"import _{name}_editable", *package_paths, ""])
    return {
        f"_{name}_editable.py": editable_txt.encode(),
        f"_{name}_editable.pth": pth_import_paths.encode(),
    }


def editable_inplace_files(*, name: str, packages: Iterable[str]) -> dict[str, bytes]:
    return {f"_{name}_editable.pth": "\n".join(packages).encode()}


def get_packages(
    *,
    packages: Sequence[str] | Mapping[str, str] | None,
    name: str,
) -> dict[str, str]:
    if packages is not None:
        if isinstance(packages, Mapping):
            return dict(packages)
        return {str(Path(p).name): p for p in packages}

    discovered_packages = {}
    for base_path in (Path("src"), Path("python"), Path()):
        path = base_path / name
        if path.is_dir() and (
            (path / "__init__.py").is_file() or (path / "__init__.pyi").is_file()
        ):
            discovered_packages[name] = str(path)
            break

    return discovered_packages


def mapping_to_modules(mapping: dict[str, str], libdir: Path) -> dict[str, str]:
    """
    Convert a mapping of files to modules to a mapping of modules to installed files.
    """
    result: dict[str, str] = {}
    for k, v in mapping.items():
        rel = Path(v).relative_to(libdir)
        if not is_valid_module(rel):
            continue
        module = path_to_module(rel)
        # Prefer .py/.pyc over other extensions (e.g. .pxd, .pyx) for the same module
        if module not in result or rel.suffix in (".py", ".pyc"):
            result[module] = str(Path(k).resolve())
    return result


def libdir_to_installed(libdir: Path) -> dict[str, str]:
    """
    Convert a mapping of files to modules to a mapping of modules to installed files.
    """
    return {
        path_to_module(pth): str(pth)
        for v in scantree(libdir)
        if is_valid_module(pth := v.relative_to(libdir))
    }
