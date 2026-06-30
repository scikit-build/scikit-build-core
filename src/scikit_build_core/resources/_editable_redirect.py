from __future__ import annotations

import importlib.abc
import importlib.util
import os
import subprocess
import sys

# Importing as little as possible is important, since every usage of Python
# imports this file. That's why we use this trick for TYPE_CHECKING
TYPE_CHECKING = False
if TYPE_CHECKING:
    from importlib.machinery import ModuleSpec


DIR = os.path.abspath(os.path.dirname(__file__))
MARKER = "SKBUILD_EDITABLE_SKIP"
VERBOSE = "SKBUILD_EDITABLE_VERBOSE"

__all__ = ["install"]


def __dir__() -> list[str]:
    return __all__


class FileLockIfUnix:
    def __init__(self, lock_file: str) -> None:
        self.lock_file = lock_file
        self.lock_file_fd: int | None = None

    def acquire(self) -> None:
        # Based on filelock.BaseFileLock.acquire and filelock.UnixFileLock._acquire
        try:
            import fcntl
        except ImportError:
            return
        import contextlib
        import time

        poll_interval = 0.05
        log_interval = 60
        last_log = time.perf_counter()

        while True:
            os.makedirs(os.path.dirname(self.lock_file), exist_ok=True)
            # O_CREAT without O_EXCL is a no-op on an existing file, so always
            # request it; checking os.path.exists() first only adds a TOCTOU race
            # (the file could be removed between the check and the open).
            open_flags = os.O_RDWR | os.O_TRUNC | os.O_CREAT

            fd = os.open(self.lock_file, open_flags, 0o644)
            with contextlib.suppress(PermissionError):  # Lock is not owned by this UID
                os.fchmod(fd, 0o644)
            try:
                fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except OSError:
                os.close(fd)
            else:
                self.lock_file_fd = fd
                return

            now = time.perf_counter()
            if now - last_log > log_interval:
                last_log = now
                print(f"Still waiting to acquire lock {self.lock_file}...")  # noqa: T201

            time.sleep(poll_interval)

    def release(self) -> None:
        try:
            import fcntl
        except ImportError:
            return

        assert isinstance(self.lock_file_fd, int)
        fcntl.flock(self.lock_file_fd, fcntl.LOCK_UN)
        os.close(self.lock_file_fd)


class _SkbuildMultiplexedPath:
    """
    A Traversable that merges multiple filesystem directories.

    Used to combine source-tree and CMake-install-tree paths so that
    importlib.resources.files() can see files from both locations.
    Fallback for Python < 3.12, whose importlib.resources.readers.MultiplexedPath
    mishandles slash-containing joinpath() calls across search locations.
    """

    def __init__(self, *paths: str) -> None:
        from pathlib import Path

        self._paths = [Path(p) for p in paths if os.path.isdir(p)]

    @property
    def name(self) -> str:
        return self._paths[0].name if self._paths else ""

    def is_dir(self) -> bool:
        return True

    def is_file(self) -> bool:
        return False

    def open(self, *args: object, **kwargs: object) -> object:
        raise IsADirectoryError(self._paths[0] if self._paths else "")

    def read_bytes(self) -> bytes:
        raise IsADirectoryError

    def read_text(self, encoding: str | None = None) -> str:
        raise IsADirectoryError

    def iterdir(self) -> object:
        seen: dict[str, object] = {}
        for base in self._paths:
            for child in base.iterdir():
                if child.name not in seen:
                    seen[child.name] = child
        return iter(seen.values())

    def joinpath(self, *descendants: object) -> object:
        if not descendants:
            return self
        from pathlib import Path

        first = str(descendants[0])
        rest = descendants[1:]
        parts = first.split("/")
        child_name, extra = parts[0], parts[1:]

        candidates = [p / child_name for p in self._paths if (p / child_name).exists()]
        if not candidates:
            return (self._paths[0] / child_name) if self._paths else Path(child_name)
        if len(candidates) == 1 or not all(c.is_dir() for c in candidates):
            result: object = candidates[0]
        else:
            result = _SkbuildMultiplexedPath(*[str(c) for c in candidates])
        for part in extra:
            result = result / part  # type: ignore[operator]
        for desc in rest:
            result = result / str(desc)  # type: ignore[operator]
        return result

    def __truediv__(self, child: object) -> object:
        return self.joinpath(str(child))

    def __repr__(self) -> str:
        paths = ", ".join(f"'{p}'" for p in self._paths)
        return f"_SkbuildMultiplexedPath({paths})"


class _ScikitBuildEditableReader:
    """
    Resource reader for editable installs with multiple package roots.

    Provides importlib.resources.files() access across both the source tree
    and the CMake install tree.
    """

    def __init__(self, paths: list[str]) -> None:
        self._paths = paths

    def files(self) -> object:
        from pathlib import Path

        existing = [p for p in self._paths if os.path.isdir(p)]
        if not existing:
            return Path(self._paths[0]) if self._paths else Path(".")
        if len(existing) == 1:
            return Path(existing[0])
        if sys.version_info >= (3, 12):
            # The stdlib MultiplexedPath is only reliable on 3.12+.  On 3.11
            # and earlier, joinpath() with a slash-containing path (e.g.
            # "namespace1/generated_data") falls back to the first search
            # location instead of navigating across them, so we use the
            # _SkbuildMultiplexedPath fallback below.
            from importlib.resources.readers import MultiplexedPath

            return MultiplexedPath(*[Path(p) for p in existing])
        return _SkbuildMultiplexedPath(*existing)

    def open_resource(self, resource: str) -> object:
        return self.files().joinpath(resource).open("rb")  # type: ignore[attr-defined]

    def resource_path(self, resource: str) -> str:
        path = self.files().joinpath(resource)  # type: ignore[attr-defined]
        if hasattr(path, "__fspath__"):
            return str(path)
        msg = f"{resource!r} is not available as a concrete file path"
        raise FileNotFoundError(msg)

    def is_resource(self, name: str) -> bool:
        path = self.files().joinpath(name)  # type: ignore[attr-defined]
        return hasattr(path, "is_file") and path.is_file()

    def contents(self) -> object:
        return (item.name for item in self.files().iterdir())  # type: ignore[attr-defined]


class _ScikitBuildLoaderWrapper:
    """
    Thin wrapper around a module loader that adds an on-demand ``rebuild()`` hook.

    Delegates all loader functionality to the wrapped loader, adding only a
    ``rebuild()`` method that runs the same CMake build/install the import-time
    auto-rebuild uses. This lets a user trigger a rebuild explicitly via
    ``module.__loader__.rebuild()`` without enabling ``editable.rebuild``.
    """

    def __init__(self, loader: object, finder: ScikitBuildRedirectingFinder) -> None:
        self._skbuild_loader = loader
        self._skbuild_finder = finder

    def __getattr__(self, name: str) -> object:
        return getattr(self._skbuild_loader, name)

    def rebuild(self) -> None:
        # User-initiated, so a missing build directory is an error rather than
        # the silent no-op the import-time auto-rebuild uses.
        self._skbuild_finder.rebuild(required=True)


class _ScikitBuildResourceLoaderWrapper(_ScikitBuildLoaderWrapper):
    """
    Loader wrapper that also provides multi-path resource reading.

    Extends the rebuild hook of the base wrapper, additionally overriding
    get_resource_reader() to return a reader covering all search paths (both
    source and CMake install trees).
    """

    def __init__(
        self,
        loader: object,
        finder: ScikitBuildRedirectingFinder,
        search_paths: list[str],
    ) -> None:
        super().__init__(loader, finder)
        self._skbuild_paths = search_paths

    def get_resource_reader(self, module_name: str) -> _ScikitBuildEditableReader:
        return _ScikitBuildEditableReader(self._skbuild_paths)


class _ScikitBuildNamespaceLoader:
    """
    Loader for a synthesized namespace package (a tracked directory with no
    importable __init__).

    Returning None from create_module and doing nothing in exec_module mirrors
    namespace-package semantics, while __path__ (set on the spec) carries every
    tracked search location. A dedicated loader -- rather than a loader-less
    namespace spec -- is required so importlib.resources can read data across
    all locations: the stdlib NamespaceReader only accepts a real
    _NamespacePath, which cannot be constructed from remapped directories.
    """

    def __init__(
        self, search_paths: list[str], finder: ScikitBuildRedirectingFinder
    ) -> None:
        self._skbuild_paths = search_paths
        self._skbuild_finder = finder

    def create_module(self, spec: object) -> object:
        return None

    def exec_module(self, module: object) -> None:
        return None

    def get_resource_reader(self, module_name: str) -> _ScikitBuildEditableReader:
        return _ScikitBuildEditableReader(self._skbuild_paths)

    def rebuild(self) -> None:
        # User-initiated, so a missing build directory is an error rather than
        # the silent no-op the import-time auto-rebuild uses.
        self._skbuild_finder.rebuild(required=True)


def _patch_importlib_resources_for_python39() -> None:
    """
    Make importlib.resources.files() honor the editable resource reader on Python 3.9.

    Python 3.9 ignores get_resource_reader().files() and falls back to
    Path(spec.origin).parent, which points at the source tree for editable
    installs. Patch that fallback so redirect packages can expose build-tree
    resources there too.
    """

    if sys.version_info[:2] != (3, 9):
        return

    from importlib.resources import _common  # type: ignore[attr-defined]

    if getattr(_common, "_skbuild_editable_patched", False):
        return

    original_fallback_resources = _common.fallback_resources

    def fallback_resources(spec: object) -> object:
        loader = getattr(spec, "loader", None)
        if isinstance(
            loader, (_ScikitBuildResourceLoaderWrapper, _ScikitBuildNamespaceLoader)
        ):
            return loader.get_resource_reader(getattr(spec, "name", "")).files()
        return original_fallback_resources(spec)

    _common.fallback_resources = fallback_resources
    _common._skbuild_editable_patched = True  # pylint: disable=protected-access


class ScikitBuildRedirectingFinder(importlib.abc.MetaPathFinder):
    def __init__(
        self,
        known_source_files: dict[str, str],
        known_wheel_files: dict[str, str],
        known_directories: dict[str, list[str]],
        known_packages: list[str],
        path: str | None,
        rebuild: bool,
        verbose: bool,
        build_options: list[str],
        install_options: list[str],
        dir: str,  # noqa: A002
        install_dir: str,
    ) -> None:
        self.known_source_files = known_source_files
        self.known_wheel_files = known_wheel_files
        self.path = path
        self.rebuild_flag = rebuild
        self.rebuilt = False
        self.verbose = verbose
        self.build_options = build_options
        self.install_options = install_options
        self.dir = dir
        self.install_dir = os.path.join(DIR, install_dir)

        # Construct the __path__ of all package-like objects. known_directories
        # maps each package to the directories that make up its __path__,
        # covering importable modules and data/resource files alike (so
        # importlib.resources can navigate directories that hold only data).
        # Install-tree paths are relative and joined with this file's directory;
        # source-tree paths are already absolute.
        submodule_search_locations: dict[str, set[str]] = {}
        for parent, parent_paths in known_directories.items():
            locations = submodule_search_locations.setdefault(parent, set())
            for parent_path in parent_paths:
                if not os.path.isabs(parent_path):
                    parent_path = os.path.join(self.dir, parent_path)  # noqa: PLW2901
                locations.add(parent_path)
        pkgs = list(known_packages)
        # Second pass: propagate build-tree paths from parent packages to
        # sub-packages.  This covers the case where a Python package (with
        # __init__.py) lives in a directory that also contains CMake-generated
        # data files but has no Python modules of its own in the build tree, so
        # the first pass never registers the build-tree directory for it.
        # Processing in depth order ensures parents are resolved before children.
        for pkg in sorted(pkgs, key=lambda p: p.count(".")):
            parent = ".".join(pkg.split(".")[:-1])
            last = pkg.split(".")[-1]
            if not parent or parent not in submodule_search_locations:
                continue
            for parent_path in sorted(submodule_search_locations[parent]):
                sub_path = os.path.join(parent_path, last)
                if (
                    os.path.isdir(sub_path)
                    and sub_path not in submodule_search_locations[pkg]
                ):
                    submodule_search_locations[pkg].add(sub_path)

        self.submodule_search_locations = submodule_search_locations
        self.pkgs = frozenset(pkgs)

    def find_spec(
        self,
        fullname: str,
        path: object = None,
        target: object = None,
    ) -> ModuleSpec | None:
        # If no known submodule_search_locations is found, it means it is a root
        # module.
        if fullname in self.submodule_search_locations:
            submodule_search_locations = list(self.submodule_search_locations[fullname])
        else:
            submodule_search_locations = None

        if fullname in self.known_wheel_files:
            # Debounce to once per process: importing a project can resolve many
            # known wheel files, but a single rebuild covers them all. Set the
            # flag before rebuilding so a raising build doesn't loop (the import
            # error propagates normally). The MARKER env var and file lock in
            # rebuild() handle cross-process recursion, not this case.
            if self.rebuild_flag and not self.rebuilt:
                self.rebuilt = True
                self.rebuild()
            origin = os.path.join(self.dir, self.known_wheel_files[fullname])
            return self._make_spec(fullname, origin, submodule_search_locations)
        if fullname in self.known_source_files:
            origin = self.known_source_files[fullname]
            return self._make_spec(fullname, origin, submodule_search_locations)

        # A tracked package directory without an importable __init__ is a
        # namespace package.
        if submodule_search_locations is not None:
            loader = _ScikitBuildNamespaceLoader(submodule_search_locations, self)
            spec = importlib.util.spec_from_loader(
                fullname,
                loader,  # type: ignore[arg-type]
                is_package=True,
            )
            if spec is not None:
                spec.submodule_search_locations = submodule_search_locations
            return spec
        return None

    def _make_spec(
        self,
        fullname: str,
        origin: str,
        submodule_search_locations: list[str] | None,
    ) -> ModuleSpec | None:
        is_pkg = origin.endswith(("__init__.py", "__init__.pyc"))
        spec = importlib.util.spec_from_file_location(
            fullname,
            origin,
            submodule_search_locations=submodule_search_locations if is_pkg else None,
        )
        # Wrap the loader so it exposes a rebuild() hook (reachable as
        # module.__loader__.rebuild()). Packages with more than one search
        # location (e.g. a source tree and a CMake install tree) additionally get
        # a resource reader so importlib.resources.files() can see resources from
        # every location, not just origin's directory.
        if spec is not None and spec.loader is not None:
            if (
                is_pkg
                and submodule_search_locations
                and len(submodule_search_locations) > 1
            ):
                spec.loader = _ScikitBuildResourceLoaderWrapper(  # type: ignore[assignment]
                    spec.loader, self, submodule_search_locations
                )
            else:
                spec.loader = _ScikitBuildLoaderWrapper(spec.loader, self)  # type: ignore[assignment]
        return spec

    def rebuild(self, *, required: bool = False) -> None:
        # Without a persistent build directory there is nothing to rebuild. The
        # import-time auto-rebuild treats this as a silent no-op; an explicit
        # caller (module.__loader__.rebuild()) sets required=True to get an error
        # instead.
        if not self.path:
            if required:
                msg = (
                    "Cannot rebuild: this editable install has no persistent "
                    "build directory. Reinstall with a 'build-dir' set (e.g. "
                    "-Cbuild-dir=build) to enable on-demand rebuilds."
                )
                raise RuntimeError(msg)
            return

        env = os.environ.copy()
        # Protect against recursion
        if self.path in env.get(MARKER, "").split(os.pathsep):
            return

        env[MARKER] = os.pathsep.join((env.get(MARKER, ""), self.path))

        verbose = self.verbose or bool(env.get(VERBOSE, ""))
        if env.get(VERBOSE, "") == "0":
            verbose = False
        if verbose:
            print(f"Running cmake --build & --install in {self.path}")  # noqa: T201

        def run_checked(command: list[str]) -> None:
            result = subprocess.run(
                command,
                cwd=self.path,
                stdout=sys.stderr if verbose else subprocess.PIPE,
                env=env,
                check=False,
                text=True,
            )
            # When verbose, output was already streamed live to stderr. When not
            # verbose, stdout was captured, so surface it here so build errors
            # (e.g. from MSBuild, which writes to stdout) are not lost.
            if result.returncode and not verbose:
                print(  # noqa: T201
                    f"ERROR: {result.stdout}",
                    file=sys.stderr,
                )
            result.check_returncode()

        lock = FileLockIfUnix(os.path.join(self.path, "editable_rebuild.lock"))

        try:
            lock.acquire()
            run_checked(["cmake", "--build", ".", *self.build_options])
            run_checked(
                [
                    "cmake",
                    "--install",
                    ".",
                    "--prefix",
                    self.install_dir,
                    *self.install_options,
                ]
            )
        finally:
            lock.release()


def install(
    known_source_files: dict[str, str],
    known_wheel_files: dict[str, str],
    known_directories: dict[str, list[str]] | None = None,
    known_packages: list[str] | None = None,
    path: str | None = None,
    rebuild: bool = False,
    verbose: bool = False,
    build_options: list[str] | None = None,
    install_options: list[str] | None = None,
    install_dir: str = "",
) -> None:
    """
    Install a meta path finder that redirects imports to the source files, and
    optionally rebuilds if path is given.

    :param known_source_files: A mapping of module names to source files
    :param known_wheel_files: A mapping of module names to wheel files
    :param known_directories: A mapping of package names to the directories that
                              make up their __path__ (covers data-only dirs)
    :param known_packages: The packages that have an __init__ (regular packages)
    :param path: The path to the build directory, or None
    :param verbose: Whether to print the cmake commands (also controlled by the
                    SKBUILD_EDITABLE_VERBOSE environment variable)
    :param install_dir: The wheel install directory override, if one was
                        specified
    """
    known_directories = known_directories or {}
    known_packages = known_packages or []
    # PEP 829 .start entry points may be invoked more than once (e.g. CPython
    # 3.15.0b1 processes a venv's site-packages twice during startup), unlike a
    # .pth `import` line whose side effects run once via the module cache.
    # Guard against installing a duplicate finder, but only for *this* package:
    # several scikit-build-core editable packages can share an environment, each
    # with its own finder and module mappings, so the check is keyed to the
    # module maps rather than rejecting any existing finder.
    for finder in sys.meta_path:
        if (
            isinstance(finder, ScikitBuildRedirectingFinder)
            and finder.known_source_files == known_source_files
            and finder.known_wheel_files == known_wheel_files
        ):
            return
    _patch_importlib_resources_for_python39()
    sys.meta_path.insert(
        0,
        ScikitBuildRedirectingFinder(
            known_source_files,
            known_wheel_files,
            known_directories,
            known_packages,
            path,
            rebuild,
            verbose,
            build_options or [],
            install_options or [],
            DIR,
            install_dir,
        ),
    )
