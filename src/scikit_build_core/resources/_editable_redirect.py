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
            open_flags = os.O_RDWR | os.O_TRUNC
            if not os.path.exists(self.lock_file):
                open_flags |= os.O_CREAT

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
    Works on Python 3.8+ without requiring importlib.resources.readers.
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
        return _SkbuildMultiplexedPath(*existing)


class _ScikitBuildResourceLoaderWrapper:
    """
    Thin wrapper around a module loader that provides multi-path resource reading.

    Delegates all loader functionality to the wrapped loader, overriding only
    get_resource_reader() to return a reader covering all search paths (both
    source and CMake install trees).
    """

    def __init__(self, loader: object, search_paths: list[str]) -> None:
        self._skbuild_loader = loader
        self._skbuild_paths = search_paths

    def __getattr__(self, name: str) -> object:
        return getattr(self._skbuild_loader, name)

    def get_resource_reader(self, module_name: str) -> _ScikitBuildEditableReader:
        return _ScikitBuildEditableReader(self._skbuild_paths)


class ScikitBuildRedirectingFinder(importlib.abc.MetaPathFinder):
    def __init__(
        self,
        known_source_files: dict[str, str],
        known_wheel_files: dict[str, str],
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
        self.verbose = verbose
        self.build_options = build_options
        self.install_options = install_options
        self.dir = dir
        self.install_dir = os.path.join(DIR, install_dir)

        # Construct the __path__ of all resource files
        # I.e. the paths of all package-like objects
        submodule_search_locations: dict[str, set[str]] = {}
        pkgs: list[str] = []
        # Loop over both python native source files and cmake installed ones
        for tree in (known_source_files, known_wheel_files):
            for module, file in tree.items():
                # Strip the last element of the module
                parent = ".".join(module.split(".")[:-1])
                # Check if it is a package
                if "__init__.py" in file:
                    parent = module
                    pkgs.append(parent)
                # Skip if it's a root module (there are no search paths for these)
                if not parent:
                    continue
                # Initialize the tree element if needed
                submodule_search_locations.setdefault(parent, set())
                # Add the parent path to the dictionary values
                parent_path = os.path.dirname(file)
                if not parent_path:
                    # root modules are skipped so all files should be in a parent package
                    msg = f"Unexpected path to source file: {file} [{module}]"
                    raise ImportError(msg)
                if not os.path.isabs(parent_path):
                    parent_path = os.path.join(self.dir, parent_path)
                submodule_search_locations[parent].add(parent_path)
        # Second pass: propagate build-tree paths from parent packages to
        # sub-packages.  This covers the case where a Python package (with
        # __init__.py) lives in a directory that also contains CMake-generated
        # data files but has no Python modules of its own in the build tree.
        # Processing in depth order ensures parents are resolved before children.
        for pkg in sorted(pkgs, key=lambda p: p.count(".")):
            parent = ".".join(pkg.split(".")[:-1])
            last = pkg.split(".")[-1]
            if not parent or parent not in submodule_search_locations:
                continue
            for parent_path in submodule_search_locations[parent]:
                sub_path = os.path.join(parent_path, last)
                if os.path.isdir(sub_path):
                    submodule_search_locations[pkg].add(sub_path)

        self.submodule_search_locations = submodule_search_locations
        self.pkgs = pkgs

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
            redir = self.known_wheel_files[fullname]
            if self.rebuild_flag:
                self.rebuild()
            is_pkg = redir.endswith(("__init__.py", "__init__.pyc"))
            spec = importlib.util.spec_from_file_location(
                fullname,
                os.path.join(self.dir, redir),
                submodule_search_locations=submodule_search_locations
                if is_pkg
                else None,
            )
            if spec is not None and is_pkg and submodule_search_locations:
                spec.loader = _ScikitBuildResourceLoaderWrapper(  # type: ignore[assignment]
                    spec.loader, submodule_search_locations
                )
            return spec
        if fullname in self.known_source_files:
            redir = self.known_source_files[fullname]
            is_pkg = redir.endswith(("__init__.py", "__init__.pyc"))
            spec = importlib.util.spec_from_file_location(
                fullname,
                redir,
                submodule_search_locations=submodule_search_locations
                if is_pkg
                else None,
            )
            if spec is not None and is_pkg and submodule_search_locations:
                spec.loader = _ScikitBuildResourceLoaderWrapper(  # type: ignore[assignment]
                    spec.loader, submodule_search_locations
                )
            return spec
        return None

    def rebuild(self) -> None:
        # Don't rebuild if not set to a local path
        if not self.path:
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

        lock = FileLockIfUnix(os.path.join(self.path, "editable_rebuild.lock"))

        try:
            lock.acquire()

            result = subprocess.run(
                ["cmake", "--build", ".", *self.build_options],
                cwd=self.path,
                stdout=sys.stderr if verbose else subprocess.PIPE,
                env=env,
                check=False,
                text=True,
            )
            if result.returncode and verbose:
                print(  # noqa: T201
                    f"ERROR: {result.stdout}",
                    file=sys.stderr,
                )
            result.check_returncode()

            result = subprocess.run(
                [
                    "cmake",
                    "--install",
                    ".",
                    "--prefix",
                    self.install_dir,
                    *self.install_options,
                ],
                cwd=self.path,
                stdout=sys.stderr if verbose else subprocess.PIPE,
                env=env,
                check=False,
                text=True,
            )
            if result.returncode and verbose:
                print(  # noqa: T201
                    f"ERROR: {result.stdout}",
                    file=sys.stderr,
                )
            result.check_returncode()
        finally:
            lock.release()


def install(
    known_source_files: dict[str, str],
    known_wheel_files: dict[str, str],
    path: str | None,
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
    :param path: The path to the build directory, or None
    :param verbose: Whether to print the cmake commands (also controlled by the
                    SKBUILD_EDITABLE_VERBOSE environment variable)
    :param install_dir: The wheel install directory override, if one was
                        specified
    """
    sys.meta_path.insert(
        0,
        ScikitBuildRedirectingFinder(
            known_source_files,
            known_wheel_files,
            path,
            rebuild,
            verbose,
            build_options or [],
            install_options or [],
            DIR,
            install_dir,
        ),
    )
