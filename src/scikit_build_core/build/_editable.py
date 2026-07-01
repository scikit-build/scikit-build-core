from __future__ import annotations

__lazy_modules__ = {
    f"{(__spec__.parent or '').rsplit('.', 1)[0]}.resources",
    f"{__spec__.parent}._pathutil",
    "pathlib",
}

import os
import sys
from collections.abc import Mapping
from pathlib import Path

from ..resources import resources
from ._pathutil import (
    editable_rebuild_install_dir,
    is_module,
    is_trackable,
    module_loader_rank,
    path_to_module,
    scantree,
)

TYPE_CHECKING = False

if TYPE_CHECKING:
    from collections.abc import Iterable, Sequence

    from ..settings.skbuild_model import ScikitBuildSettings

__all__ = [
    "collect_search_locations",
    "editable_inplace",
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
    install_prefix: str | None = None,
) -> dict[str, bytes]:
    """
    Build the editable redirect files for a package.

    On Python 3.15+ (PEP 829), the ``import`` line that runs the redirect is
    moved out of the ``.pth`` file (where it is deprecated) into a ``.start``
    file, and the ``.pth`` keeps only the ``sys.path`` entries. ``use_start``
    overrides this auto-detection (used by tests); leave it ``None`` to select
    based on the running interpreter.

    ``install_prefix`` selects where the redirect looks for CMake-installed
    files. When ``None`` (the default), they are recorded relative to the
    redirect file -- the install tree ships in the wheel and lands in
    site-packages. When set (a rebuildable editable with a persistent build-dir),
    the install tree lives outside the wheel: ``installed`` and the install-tree
    search locations are absolute, and ``install_prefix`` is the
    ``cmake --install --prefix`` used on rebuild.
    """
    if use_start is None:
        use_start = sys.version_info >= (3, 15)
    external_install = install_prefix is not None
    modules = mapping_to_modules(mapping, libdir)
    installed = libdir_to_installed(libdir, absolute=external_install)
    directories, known_packages = collect_search_locations(
        mapping, libdir, absolute=external_install
    )
    rebuild = settings.editable.rebuild_enabled
    if install_prefix is not None:
        # The persistent install tree lives outside the wheel, so the shim is
        # given an absolute prefix (os.path.join drops DIR for an absolute path)
        # and references the installed files by absolute path.
        install_dir = install_prefix
    else:
        install_dir = settings.wheel.install_dir
        if rebuild:
            # The shim joins install_dir onto the platlib root; a platlib/purelib
            # selector reduces to its remainder, any other tree is rejected.
            install_dir = editable_rebuild_install_dir(install_dir)
    editable_txt = editable_redirect(
        modules=modules,
        installed=installed,
        directories=directories,
        packages=known_packages,
        reload_dir=reload_dir,
        rebuild=rebuild,
        verbose=settings.editable.verbose,
        build_options=build_options,
        install_options=install_options,
        install_dir=install_dir,
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


def editable_inplace(
    *,
    known_packages: Sequence[str],
    search_paths: Sequence[str],
    path: str | None,
    rebuild: bool,
    verbose: bool,
    build_options: Sequence[str],
    as_entrypoint: bool = False,
) -> str:
    """
    Prepare the contents of the inplace editable shim.

    Like :func:`editable_redirect` but appends an ``install_inplace(...)`` call
    (or an ``entrypoint()`` wrapper for PEP 829 ``.start`` files). The finder it
    installs leaves import resolution to Python and only adds
    ``module.__loader__.rebuild()`` to the inplace-built packages.
    """
    editable_py = resources / "_editable_redirect.py"
    editable_txt: str = editable_py.read_text(encoding="utf-8")

    arguments = (
        list(known_packages),
        list(search_paths),
        path,
        rebuild,
        verbose,
        list(build_options),
    )
    arguments_str = ", ".join(repr(x) for x in arguments)
    if as_entrypoint:
        editable_txt += (
            f"\n\ndef entrypoint() -> None:\n    install_inplace({arguments_str})\n"
        )
    else:
        editable_txt += f"\n\ninstall_inplace({arguments_str})\n"
    return editable_txt


def editable_inplace_files(
    *,
    name: str,
    packages: Mapping[str, str],
    package_paths: Sequence[str],
    source_dir: Path | None,
    build_options: Sequence[str] = (),
    settings: ScikitBuildSettings,
    use_start: bool | None = None,
) -> dict[str, bytes]:
    """
    Build the inplace editable files for a package.

    Emits a shim that installs a finder exposing ``module.__loader__.rebuild()``
    (and, when :confval:`editable.rebuild` is on, rebuilds on first import), plus
    a ``.pth`` adding the package source directories to ``sys.path``. Mirrors the
    file/``use_start`` layout of :func:`editable_redirect_files`.
    """
    if use_start is None:
        use_start = sys.version_info >= (3, 15)
    # The importable top-level name is the entry's leaf with any module suffix
    # stripped -- a package dir keeps its name (``mypkg``), a single-module entry
    # drops the extension (``hello.py`` -> ``hello``, #888) so it matches the
    # finder's ``fullname.partition(".")[0]`` check.
    known_packages = sorted({Path(v).name.partition(".")[0] for v in packages.values()})
    editable_txt = editable_inplace(
        known_packages=known_packages,
        search_paths=list(package_paths),
        path=os.fspath(source_dir) if source_dir else None,
        rebuild=settings.editable.rebuild_enabled,
        verbose=settings.editable.verbose,
        build_options=build_options,
        as_entrypoint=use_start,
    )
    package_lines = list(package_paths)
    files = {f"_editable_skbc_{name}.py": editable_txt.encode()}
    if use_start:
        # PEP 829: the import callable lives in a UTF-8-sig encoded .start file,
        # and the .pth carries only sys.path entries (if any).
        files[f"_editable_skbc_{name}.start"] = (
            f"_editable_skbc_{name}:entrypoint".encode("utf-8-sig")
        )
        if package_lines:
            files[f"_editable_skbc_{name}.pth"] = "\n".join(
                [*package_lines, ""]
            ).encode()
    else:
        files[f"_editable_skbc_{name}.pth"] = "\n".join(
            [f"import _editable_skbc_{name}", *package_lines, ""]
        ).encode()
    return files


def get_packages(
    *,
    packages: Sequence[str] | Mapping[str, str] | None,
    name: str,
) -> dict[str, str]:
    if packages is not None:
        if isinstance(packages, Mapping):
            return dict(packages)
        return {str(Path(p).name): p for p in packages}

    # ``name`` is the raw distribution name. A '.' may mark a namespace-package
    # (PEP 420) boundary; '-' always becomes '_' (importable)
    parts = [part.replace("-", "_") for part in name.split(".")]

    # The flat, single-directory name ("ns_pkg") is tried first. A dotted name
    # also tries the nested namespace layout ("ns/pkg"), where only the leaf
    # needs an ``__init__``.
    rel_candidates = ["_".join(parts)]
    if len(parts) > 1:
        rel_candidates.append("/".join(parts))

    for base_path in (Path("src"), Path("python"), Path()):
        for rel in rel_candidates:
            path = base_path / rel
            if path.is_dir() and (
                (path / "__init__.py").is_file() or (path / "__init__.pyi").is_file()
            ):
                return {rel: str(path)}

    return {}


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
        if not is_trackable(rel) or not is_module(rel):
            continue
        module = path_to_module(rel)
        if module in result and not _prefer_module(rel, selected[module]):
            continue
        # Make the source path absolute, but do not resolve symlinks
        result[module] = str(Path(k).absolute())
        selected[module] = rel
    return result


def libdir_to_installed(libdir: Path, *, absolute: bool = False) -> dict[str, str]:
    """
    Map importable module names to their installed files (relative to ``libdir``).

    Only importable files are included; data/resource files are tracked
    separately by :func:`collect_search_locations`.

    With ``absolute``, the paths are emitted absolute rather than relative to
    ``libdir`` -- used when the install tree lives outside the wheel (a
    rebuildable editable pointing at a persistent build-dir).
    """
    result: dict[str, str] = {}
    selected: dict[str, Path] = {}
    for v in scantree(libdir):
        pth = v.relative_to(libdir)
        if not is_trackable(pth) or not is_module(pth):
            continue
        module = path_to_module(pth)
        if module in result and not _prefer_module(pth, selected[module]):
            continue
        result[module] = str(v if absolute else pth)
        selected[module] = pth
    return result


def collect_search_locations(
    mapping: dict[str, str], libdir: Path, *, absolute: bool = False
) -> tuple[dict[str, list[str]], list[str]]:
    """
    Build the package search-location map and the list of regular packages.

    Every tracked file -- importable modules *and* data/resource files -- adds
    its directory to its package's ``__path__``, so ``importlib.resources`` can
    reach data even in a directory that holds no importable module (e.g. CMake
    installs only data into a package dir). Keeping this separate from the
    module-resolution maps means a non-importable file is never a module's origin.

    Source-tree directories are absolute, install-tree ones relative to
    ``libdir`` (or absolute when ``absolute`` is set, for an install tree that
    lives outside the wheel). Returns ``(directories, packages)`` where
    ``packages`` are the modules whose directory holds an ``__init__`` (including
    ``.pxd``/``.pyx``).
    """
    # Collect (module, directory, is_init) entries. Source tree: the absolute
    # source file's parent. Install tree: the directory relative to libdir.
    entries: list[tuple[str, str, bool]] = []
    for source, target in mapping.items():
        rel = Path(target).relative_to(libdir)
        if is_trackable(rel):
            src = Path(source).absolute()
            entries.append((path_to_module(rel), str(src.parent), _is_init(src.name)))
    for v in scantree(libdir):
        rel = v.relative_to(libdir)
        if is_trackable(rel):
            directory = str(v.parent if absolute else rel.parent)
            entries.append((path_to_module(rel), directory, _is_init(rel.name)))

    directories: dict[str, set[str]] = {}
    packages: set[str] = set()
    for module, directory, is_init in entries:
        if is_init:
            packages.add(module)
            parent = module
        else:
            parent = module.rpartition(".")[0]
        if parent:
            directories.setdefault(parent, set()).add(directory)

    return (
        {pkg: sorted(dirs) for pkg, dirs in directories.items()},
        sorted(packages),
    )


def _is_init(name: str) -> bool:
    return name.partition(".")[0] == "__init__"


def _prefer_module(candidate: Path, current: Path) -> bool:
    """
    Whether ``candidate`` outranks ``current`` for the same module name, by
    import loader precedence (see :func:`module_loader_rank`).
    """
    return module_loader_rank(candidate) < module_loader_rank(current)
