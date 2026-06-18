from __future__ import annotations

import os
import sys
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
    as_entrypoint: bool = False,
) -> str:
    """
    Prepare the contents of the _editable_redirect.py file.

    If ``as_entrypoint`` is set, the install call is wrapped in a zero-argument
    ``entrypoint()`` function (for PEP 829 ``.start`` files) rather than being
    invoked at module import time (for the legacy ``.pth`` ``import`` line).
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
    if as_entrypoint:
        editable_txt += f"\n\ndef entrypoint() -> None:\n    install({arguments_str})\n"
    else:
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
    use_start: bool | None = None,
) -> dict[str, bytes]:
    """
    Build the editable redirect files for a package.

    On Python 3.15+ (PEP 829), the ``import`` line that runs the redirect is
    moved out of the ``.pth`` file (where it is deprecated) into a ``.start``
    file, and the ``.pth`` keeps only the ``sys.path`` entries. ``use_start``
    overrides this auto-detection (used by tests); leave it ``None`` to select
    based on the running interpreter.
    """
    if use_start is None:
        use_start = sys.version_info >= (3, 15)
    modules = mapping_to_modules(mapping, libdir)
    installed = libdir_to_installed(libdir)
    if settings.editable.rebuild and settings.wheel.install_dir.startswith("/"):
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
        as_entrypoint=use_start,
    )
    package_paths = tuple(packages)
    files = {f"_editable_skbc_{name}.py": editable_txt.encode()}
    if use_start:
        # PEP 829: the import callable lives in a UTF-8-sig encoded .start file,
        # and the .pth carries only sys.path entries (if any).
        files[f"_editable_skbc_{name}.start"] = (
            f"_editable_skbc_{name}:entrypoint".encode("utf-8-sig")
        )
        if package_paths:
            files[f"_editable_skbc_{name}.pth"] = "\n".join(
                [*package_paths, ""]
            ).encode()
    else:
        pth_import_paths = "\n".join(
            [f"import _editable_skbc_{name}", *package_paths, ""]
        )
        files[f"_editable_skbc_{name}.pth"] = pth_import_paths.encode()
    return files


def editable_inplace_files(*, name: str, packages: Iterable[str]) -> dict[str, bytes]:
    return {f"_editable_skbc_{name}.pth": "\n".join(packages).encode()}


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
