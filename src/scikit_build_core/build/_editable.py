from __future__ import annotations

import os
import sys
import typing
from collections.abc import Mapping
from pathlib import Path

from ..resources import resources
from ._pathutil import (
    is_module,
    is_valid_module,
    module_loader_rank,
    path_to_module,
    scantree,
)

if typing.TYPE_CHECKING:
    from collections.abc import Iterable, Sequence

    from ..settings.skbuild_model import ScikitBuildSettings

__all__ = [
    "collect_search_locations",
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
    directories: dict[str, list[str]],
    packages: Sequence[str],
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
        directories,
        list(packages),
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
    directories, known_packages = collect_search_locations(mapping, libdir)
    if settings.editable.rebuild and settings.wheel.install_dir.startswith("/"):
        msg = "Editable installs cannot rebuild an absolute wheel.install-dir. Use an override to change if needed."
        raise AssertionError(msg)
    editable_txt = editable_redirect(
        modules=modules,
        installed=installed,
        directories=directories,
        packages=known_packages,
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
    Map importable module names to their (absolute) source files.

    Only importable files are included; data/resource files are tracked
    separately by :func:`collect_search_locations` so that ``find_spec`` never
    resolves a name to a non-importable file.
    """
    result: dict[str, str] = {}
    selected: dict[str, Path] = {}
    for k, v in mapping.items():
        rel = Path(v).relative_to(libdir)
        if not is_valid_module(rel) or not is_module(rel):
            continue
        module = path_to_module(rel)
        if module in result and not _prefer_module(rel, selected[module]):
            continue
        # Make the source path absolute, but do not resolve symlinks
        result[module] = str(Path(k).absolute())
        selected[module] = rel
    return result


def libdir_to_installed(libdir: Path) -> dict[str, str]:
    """
    Map importable module names to their installed files (relative to ``libdir``).

    Only importable files are included; data/resource files are tracked
    separately by :func:`collect_search_locations`.
    """
    result: dict[str, str] = {}
    selected: dict[str, Path] = {}
    for v in scantree(libdir):
        pth = v.relative_to(libdir)
        if not is_valid_module(pth) or not is_module(pth):
            continue
        module = path_to_module(pth)
        if module in result and not _prefer_module(pth, selected[module]):
            continue
        result[module] = str(pth)
        selected[module] = pth
    return result


def collect_search_locations(
    mapping: dict[str, str], libdir: Path
) -> tuple[dict[str, list[str]], list[str]]:
    """
    Build the package search-location map and the list of regular packages.

    Every tracked file -- importable modules *and* data/resource files -- adds
    its directory to its package's ``__path__``, so ``importlib.resources`` can
    reach data even in a directory that holds no importable module (e.g. CMake
    installs only data into a package dir). This is kept separate from the
    module-resolution maps so a non-importable file is never returned as a
    module's origin.

    Source-tree directories are absolute; install-tree directories are relative
    to ``libdir`` (the redirect joins them with the install location at runtime).
    Returns ``(directories, packages)`` where ``packages`` are the modules whose
    directory holds an ``__init__`` (including ``.pxd``/``.pyx`` ones).
    """
    directories: dict[str, set[str]] = {}
    packages: set[str] = set()

    def add(module: str, directory: str, *, is_init: bool) -> None:
        if is_init:
            packages.add(module)
            parent = module
        else:
            parent = module.rpartition(".")[0]
        if parent:
            directories.setdefault(parent, set()).add(directory)

    # Source tree: register the (absolute) source file's parent directory.
    for source, target in mapping.items():
        rel = Path(target).relative_to(libdir)
        if not is_valid_module(rel):
            continue
        source_path = Path(source).absolute()
        add(
            path_to_module(rel),
            str(source_path.parent),
            is_init=_is_init(source_path.name),
        )

    # Install tree: register the directory relative to libdir.
    for v in scantree(libdir):
        rel = v.relative_to(libdir)
        if not is_valid_module(rel):
            continue
        add(path_to_module(rel), str(rel.parent), is_init=_is_init(rel.name))

    return (
        {pkg: sorted(dirs) for pkg, dirs in directories.items()},
        sorted(packages),
    )


def _is_init(name: str) -> bool:
    return name.partition(".")[0] == "__init__"


def _prefer_module(candidate: Path, current: Path) -> bool:
    """
    Whether ``candidate`` should replace ``current`` for the same module name.

    Files are ranked by Python's import loader precedence (extension module >
    source > bytecode > non-importable), so editable installs resolve a module
    to the same file a real wheel would import. This keeps a versioned shared
    library (``_tango.so.10``) from shadowing the real ``_tango.so`` (issue
    #1144) and an extension module from being shadowed by a ``.py`` next to it.
    """
    return module_loader_rank(candidate) < module_loader_rank(current)
