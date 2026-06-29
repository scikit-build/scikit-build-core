from __future__ import annotations

import os
import shutil
import sys
from collections import defaultdict
from collections.abc import Iterable
from fnmatch import fnmatchcase
from pathlib import Path
from typing import TYPE_CHECKING, ClassVar, Literal

import setuptools
from packaging.version import Version

from .._check_extra import warn_missing_extra
from .._compat import tomllib
from .._compat.setuptools.errors import SetupError
from .._logging import LEVEL_VALUE, raw_logger
from ..builder.builder import Builder, get_archs
from ..builder.macos import normalize_macos_version
from ..cmake import CMake, CMaker
from ..settings.skbuild_model import normalize_build_types
from ..settings.skbuild_read_settings import SettingsReader

if TYPE_CHECKING:
    from collections.abc import Callable

    from setuptools.dist import Distribution

    from ..settings.skbuild_model import ScikitBuildSettings

__all__ = [
    "BuildCMake",
    "cmake_args",
    "cmake_install_dir",
    "cmake_install_target",
    "cmake_process_manifest_hook",
    "cmake_source_dir",
    "finalize_distribution_options",
]

WRAPPER_CMAKE_INSTALL_DIR_COMPAT = "_scikit_build_wrapper_cmake_install_dir_compat"
WRAPPER_CLASSIC_LAYOUT_COMPAT = "_scikit_build_wrapper_classic_layout_compat"
ORIGINAL_DATA_FILES = "_scikit_build_original_data_files"


def __dir__() -> list[str]:
    return __all__


def _apply_cmake_install_target(
    settings: ScikitBuildSettings, dist: Distribution
) -> None:
    # Classic scikit-build's cmake_install_target picks the build target that
    # performs the install; "install" is the default cmake --install path. A
    # custom target installs via `cmake --build --target`, which is exactly what
    # install.targets does.
    target = getattr(dist, "cmake_install_target", None) or "install"
    if target != "install":
        settings.install.targets = [*settings.install.targets, target]


def _validate_settings(
    settings: ScikitBuildSettings, *, editable_mode: bool = False
) -> None:
    if settings.wheel.expand_macos_universal_tags:
        msg = "wheel.expand_macos_universal_tags is not supported in setuptools mode"
        raise SetupError(msg)
    if settings.logging.level != "WARNING":
        msg = "Logging is not adjustable in setuptools mode yet"
        raise SetupError(msg)
    if settings.wheel.py_api:
        msg = "wheel.py_api is not supported in setuptools mode, use bdist_wheel options instead"
        raise SetupError(msg)
    if editable_mode:
        if settings.editable.mode != "inplace":
            msg = "setuptools editable installs require editable.mode = 'inplace'"
            raise SetupError(msg)
        if settings.editable.rebuild:
            msg = "editable.rebuild is not supported in setuptools mode"
            raise SetupError(msg)


def _load_settings(
    state: Literal["sdist", "wheel", "editable"] = "sdist",
) -> ScikitBuildSettings:
    # setup.py-only projects (common with the classic scikit-build wrapper)
    # don't have a pyproject.toml.
    if not Path("pyproject.toml").is_file():
        return SettingsReader({}, {}, state=state).settings
    return SettingsReader.from_file("pyproject.toml", state=state).settings


def get_source_dir_from_pyproject_toml() -> str | None:
    try:
        with Path("pyproject.toml").open("rb") as f:
            source_dir: str | None = tomllib.load(f)["tool"]["scikit-build"]["cmake"][
                "source-dir"
            ]
            return source_dir
    except (FileNotFoundError, KeyError):
        return None


def _package_source_dir(dist: Distribution, package: str) -> Path:
    package_dir = getattr(dist, "package_dir", {}) or {}
    package_path = Path(*package.split("."))
    if package in package_dir:
        return Path(package_dir[package])
    if "" in package_dir:
        return Path(package_dir[""]) / package_path
    return package_path


def _package_base_dir(dist: Distribution) -> Path:
    packages = list(getattr(dist, "packages", None) or [])
    package_dir = getattr(dist, "package_dir", {}) or {}

    if not packages:
        return Path(package_dir.get("", ""))

    candidates: list[str] = []
    for package in packages:
        package_source_dir = _package_source_dir(dist, package)
        package_parts = package.split(".")
        if package_parts == list(package_source_dir.parts[-len(package_parts) :]):
            base_dir = Path(*package_source_dir.parts[: -len(package_parts)])
        else:
            base_dir = package_source_dir.parent
        candidates.append(str(base_dir))

    common_base = os.path.commonpath(candidates)
    return Path("" if common_base == "." else common_base)


def _translate_wrapper_install_dir(dist: Distribution, install_dir: str) -> Path:
    translated = Path(install_dir)
    package_base_dir = _package_base_dir(dist)
    if not package_base_dir.parts:
        return translated

    try:
        return translated.relative_to(package_base_dir)
    except ValueError:
        return translated


def _collect_recursive_files(root: Path) -> set[str]:
    if not root.exists():
        return set()

    return {
        path.relative_to(root).as_posix()
        for path in root.rglob("*")
        if path.is_file() or path.is_symlink()
    }


def _read_cmake_install_manifests(
    build_dir: Path, install_dir: Path
) -> list[str] | None:
    manifests = sorted(build_dir.glob("install_manifest*.txt"))
    if not manifests:
        return None

    install_root = install_dir.resolve()
    files: list[str] = []
    for manifest in manifests:
        for line in manifest.read_text(encoding="utf-8").splitlines():
            if not line:
                continue

            installed_path = Path(line)
            if not installed_path.is_absolute():
                installed_path = build_dir / installed_path
            # Resolve symlinks (e.g. macOS /tmp) so relative_to() can't be
            # fooled by an unresolved prefix.
            installed_path = installed_path.resolve()

            try:
                relpath = installed_path.relative_to(install_root)
            except ValueError:
                msg = (
                    "CMake-installed files must stay within the setuptools build "
                    f"directory, got: {installed_path}"
                )
                raise SetupError(msg) from None

            files.append(relpath.as_posix())

    return sorted(dict.fromkeys(files))


def _process_manifest(
    cmake_manifest: list[str],
    process_manifest: Callable[[list[str]], object] | None,
) -> list[str]:
    if process_manifest is None:
        return list(cmake_manifest)

    if not callable(process_manifest):
        msg = "cmake_process_manifest_hook must be callable"
        raise SetupError(msg)

    processed_manifest = process_manifest(list(cmake_manifest))
    if processed_manifest is None or isinstance(processed_manifest, (str, bytes)):
        msg = (
            "cmake_process_manifest_hook must return an iterable of manifest paths, "
            f"got {type(processed_manifest).__name__}"
        )
        raise SetupError(msg)

    if not isinstance(processed_manifest, Iterable):
        msg = (
            "cmake_process_manifest_hook must return an iterable of manifest paths, "
            f"got {type(processed_manifest).__name__}"
        )
        raise SetupError(msg)

    processed_list: list[str] = []
    for path in processed_manifest:
        if not isinstance(path, str):
            msg = "cmake_process_manifest_hook must return manifest paths as strings"
            raise SetupError(msg)
        processed_list.append(path)

    invalid_paths = sorted(set(processed_list) - set(cmake_manifest))
    if invalid_paths:
        msg = (
            "cmake_process_manifest_hook must return a subset of installed files, "
            f"got unexpected path: {invalid_paths[0]}"
        )
        raise SetupError(msg)

    return processed_list


def _remove_empty_parents(path: Path, root: Path) -> None:
    for candidate in [path.parent, *path.parent.parents]:
        if candidate == root:
            break
        try:
            candidate.rmdir()
        except OSError:
            break


def _prune_manifest(
    install_dir: Path, original: list[str], selected: list[str]
) -> None:
    omitted = set(original) - set(selected)
    for relative_path in sorted(
        omitted, key=lambda path: (path.count("/"), path), reverse=True
    ):
        path = install_dir / relative_path
        if not path.exists() and not path.is_symlink():
            continue

        path.unlink()
        _remove_empty_parents(path, install_dir)


def _package_paths(dist: Distribution) -> set[Path]:
    return {
        Path(*package.split(".")) for package in getattr(dist, "packages", None) or []
    }


def _package_source_roots(dist: Distribution) -> list[Path]:
    packages = list(getattr(dist, "packages", None) or [])
    if not packages:
        return [_package_base_dir(dist)]

    roots: set[Path] = set()
    for package in packages:
        package_source_dir = _package_source_dir(dist, package)
        package_parts = package.split(".")
        if package_parts == list(package_source_dir.parts[-len(package_parts) :]):
            roots.add(Path(*package_source_dir.parts[: -len(package_parts)]))
        else:
            roots.add(package_source_dir.parent)

    return sorted(roots, key=lambda path: (-len(path.parts), os.fspath(path)))


def _classify_wrapper_package_file(dist: Distribution, path: Path) -> Path | None:
    package_paths = _package_paths(dist)
    if not package_paths:
        return None

    # Files installed into a package's source directory belong to that
    # package, honoring package_dir mappings (deepest source dir first).
    packages = list(getattr(dist, "packages", None) or [])
    package_source_dirs = sorted(
        ((_package_source_dir(dist, package), package) for package in packages),
        key=lambda pair: -len(pair[0].parts),
    )
    for source_dir, package in package_source_dirs:
        if not source_dir.parts:
            continue
        try:
            remainder = path.relative_to(source_dir)
        except ValueError:
            continue
        return Path(*package.split(".")) / remainder

    candidates = [path]
    for root in _package_source_roots(dist):
        if not root.parts:
            continue
        try:
            candidates.append(path.relative_to(root))
        except ValueError:
            continue

    seen: set[Path] = set()
    for candidate in candidates:
        if candidate in seen:
            continue
        seen.add(candidate)
        if any(
            candidate == package_path or package_path in candidate.parents
            for package_path in package_paths
        ):
            return candidate

    return None


def _excluded_by_package_data(dist: Distribution, package_output: Path) -> bool:
    """Check a package file against exclude_package_data, like build_py does
    for source package data."""
    exclude = getattr(dist, "exclude_package_data", None) or {}
    if not exclude:
        return False

    # Attribute the file to its deepest containing package
    package_paths = sorted(_package_paths(dist), key=lambda p: -len(p.parts))
    for package_path in package_paths:
        if package_path in package_output.parents:
            package = ".".join(package_path.parts)
            relative = package_output.relative_to(package_path).as_posix()
            patterns = [*exclude.get(package, []), *exclude.get("", [])]
            return any(fnmatchcase(relative, pattern) for pattern in patterns)

    return False


class BuildCMake(setuptools.Command):
    source_dir: str | None = None
    cmake_args: list[str] | str | None = None
    _editable_install_dir: Path | None
    _installed_files: list[Path]

    build_lib: str | None
    build_temp: str | None
    debug: bool | None
    editable_mode: bool
    parallel: int | None
    plat_name: str | None

    user_options: ClassVar[list[tuple[str, str, str]]] = [
        ("build-lib=", "b", "directory for compiled extension modules"),
        ("build-temp=", "t", "directory for temporary files (build by-products)"),
        ("plat-name=", "p", "platform name to cross-compile for, if supported "),
        ("debug", "g", "compile/link with debugging information"),
        ("parallel=", "j", "number of parallel build jobs"),
        ("source-dir=", "s", "directory with CMakeLists.txt"),
        ("cmake-args=", "a", "extra arguments for CMake"),
    ]

    def initialize_options(self) -> None:
        self.build_lib = None
        self.build_temp = None
        self.debug = None
        self.editable_mode = False
        self.parallel = None
        self.plat_name = None
        self.source_dir = get_source_dir_from_pyproject_toml()
        self.cmake_args = None
        self._editable_install_dir = None
        self._installed_files = []

    def finalize_options(self) -> None:
        self.set_undefined_options(
            "build_ext",
            ("build_lib", "build_lib"),
            ("build_temp", "build_temp"),
            ("debug", "debug"),
            ("parallel", "parallel"),
            ("plat_name", "plat_name"),
        )
        self.editable_mode = self._get_editable_mode()

        if isinstance(self.cmake_args, str):
            self.cmake_args = [
                b.strip() for a in self.cmake_args.split() for b in a.split(";")
            ]

    def _get_editable_mode(self) -> bool:
        # editable_mode is the PEP 660 path; inplace is "build_ext --inplace"
        build_ext = self.distribution.get_command_obj("build_ext")
        return bool(getattr(build_ext, "editable_mode", False)) or bool(
            getattr(build_ext, "inplace", False)
        )

    def _get_install_subdir(self) -> Path:
        dist_cmake_install_dir = (
            getattr(self.distribution, "cmake_install_dir", "") or ""
        )
        if getattr(self.distribution, WRAPPER_CMAKE_INSTALL_DIR_COMPAT, False):
            return _translate_wrapper_install_dir(
                self.distribution, dist_cmake_install_dir
            )
        return Path(dist_cmake_install_dir)

    def _get_install_dir(self) -> Path:
        assert self.build_lib is not None
        install_subdir = self._get_install_subdir()

        if not self.editable_mode:
            return Path(self.build_lib).resolve() / install_subdir

        package_dir = getattr(self.distribution, "package_dir", {}) or {}
        source_root = package_dir.get("", ".")
        return Path(source_root).resolve() / install_subdir

    def _set_generated_data_files(
        self, data_files: list[tuple[str, list[str]]] | None = None
    ) -> None:
        dist = self.distribution
        if not hasattr(dist, ORIGINAL_DATA_FILES):
            setattr(
                dist, ORIGINAL_DATA_FILES, list(getattr(dist, "data_files", []) or [])
            )

        original_data_files = list(getattr(dist, ORIGINAL_DATA_FILES))
        dist.data_files = [*original_data_files, *(data_files or [])]

    def _record_installed_files(
        self,
        build_dir: Path,
        install_dir: Path,
        manifest_files: list[str] | None = None,
    ) -> None:
        self._editable_install_dir = install_dir
        if manifest_files is not None:
            self._installed_files = [
                (install_dir / Path(line)).resolve() for line in manifest_files if line
            ]
            return

        manifests = sorted(build_dir.glob("install_manifest*.txt"))
        if not manifests:
            self._installed_files = []
            return

        self._installed_files = []
        for manifest in manifests:
            self._installed_files.extend(
                Path(line).resolve()
                for line in manifest.read_text(encoding="utf-8").splitlines()
                if line
            )

    def _wrapper_classic_layout_compat_enabled(self) -> bool:
        return bool(
            not self.editable_mode
            and getattr(self.distribution, WRAPPER_CLASSIC_LAYOUT_COMPAT, False)
        )

    def _apply_wrapper_classic_layout_compat(
        self, *, staged_install_dir: Path, install_subdir: Path
    ) -> None:
        assert self.build_lib is not None

        build_lib = Path(self.build_lib).resolve()
        staged_install_dir = staged_install_dir.resolve()
        generated_data_files: defaultdict[str, list[str]] = defaultdict(list)
        package_outputs: list[Path] = []

        for staged_path in self._installed_files:
            relative_output = staged_path.relative_to(staged_install_dir)
            effective_output = (
                install_subdir / relative_output
                if install_subdir.parts
                else relative_output
            )
            package_output = _classify_wrapper_package_file(
                self.distribution, effective_output
            )

            # Classic scikit-build treats CMake-installed top-level Python
            # modules as py_modules rather than data files.
            if (
                package_output is None
                and len(effective_output.parts) == 1
                and effective_output.suffix == ".py"
            ):
                package_output = effective_output

            if package_output is not None and _excluded_by_package_data(
                self.distribution, package_output
            ):
                continue

            if package_output is None:
                data_dir = (
                    os.fspath(effective_output.parent)
                    if effective_output.parent.parts
                    else ""
                )
                generated_data_files[data_dir].append(os.fspath(staged_path))
                continue

            destination = build_lib / package_output
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(staged_path, destination)
            package_outputs.append(destination)

        self._installed_files = sorted(package_outputs)
        data_files = [
            (directory, sorted(files))
            for directory, files in sorted(generated_data_files.items())
        ]
        self._set_generated_data_files(data_files)

    def run(self) -> None:
        assert self.build_lib is not None
        assert self.build_temp is not None
        assert self.plat_name is not None

        warn_missing_extra("setuptools")

        self.editable_mode = self._get_editable_mode()
        # run() is always a wheel or editable build; pass the matching state so
        # overrides (if.state = "wheel"/"editable") are applied correctly.
        settings = _load_settings(state="editable" if self.editable_mode else "wheel")
        _validate_settings(settings, editable_mode=self.editable_mode)
        _apply_cmake_install_target(settings, self.distribution)

        build_tmp_folder = Path(self.build_temp)
        build_temp = build_tmp_folder / "_skbuild"
        self._installed_files = []
        self._editable_install_dir = None
        self._set_generated_data_files()

        dist = self.distribution
        dist_source_dir = getattr(self.distribution, "cmake_source_dir", None)
        source_dir = self.source_dir if dist_source_dir is None else dist_source_dir
        assert source_dir is not None, "This should not be reachable"

        assert self.cmake_args is None or isinstance(self.cmake_args, list)
        # Copy to avoid mutating self.cmake_args in place (which would
        # double-append the dist args if run() executes more than once).
        configure_args = list(self.cmake_args or [])
        dist_cmake_args = getattr(self.distribution, "cmake_args", None)
        configure_args.extend(dist_cmake_args or [])

        bdist_wheel = dist.get_command_obj("bdist_wheel")
        assert bdist_wheel is not None
        limited_api = bdist_wheel.py_limited_api

        # TODO: this is a hack due to moving temporary paths for isolation
        if build_temp.exists():
            shutil.rmtree(build_temp)

        cmake = CMake.default_search(version=settings.cmake.version)

        config = CMaker(
            cmake,
            source_dir=Path(source_dir),
            build_dir=build_temp,
            build_type=normalize_build_types(settings.cmake.build_type)[0],
        )

        builder = Builder(
            settings=settings,
            config=config,
        )

        # Setuptools requires this be specified if there's a mismatch.
        if sys.platform.startswith("darwin"):
            arm_only = get_archs(builder.config.env, builder.get_cmake_args()) == [
                "arm64"
            ]
            orig_macos_str = self.plat_name.rsplit("-", 1)[0].split("-", 1)[1]
            orig_macos = normalize_macos_version(orig_macos_str, arm=arm_only)
            config.env.setdefault("MACOSX_DEPLOYMENT_TARGET", str(orig_macos))

        builder.config.build_type = (
            "Debug"
            if self.debug
            else normalize_build_types(settings.cmake.build_type)[0]
        )

        # Setting the install prefix because some libs hardcode CMAKE_INSTALL_PREFIX
        # Otherwise `cmake --install --prefix` would work by itself
        install_subdir = self._get_install_subdir()
        install_dir = self._get_install_dir()
        use_wrapper_classic_layout_compat = (
            self._wrapper_classic_layout_compat_enabled()
        )
        cmake_install_prefix = (
            build_temp / "cmake-install" / install_subdir
            if use_wrapper_classic_layout_compat
            else install_dir
        )
        installed_before = _collect_recursive_files(cmake_install_prefix)
        defines = {"CMAKE_INSTALL_PREFIX": cmake_install_prefix}

        builder.configure(
            name=dist.get_name(),
            version=Version(dist.get_version()),
            defines=defines,
            limited_api=bool(limited_api),
            configure_args=configure_args,
        )

        # Set CMAKE_BUILD_PARALLEL_LEVEL to control the parallel build level
        # across all generators.
        build_args = []

        # self.parallel is a way to set parallel jobs by hand using -j in the
        # build_ext call, not supported by pip or PyPA-build.
        if "CMAKE_BUILD_PARALLEL_LEVEL" not in builder.config.env and self.parallel:
            build_args.append(f"-j{self.parallel}")

        builder.build(build_args=build_args)
        builder.install(install_dir=cmake_install_prefix)

        cmake_manifest = _read_cmake_install_manifests(build_temp, cmake_install_prefix)
        if cmake_manifest is None:
            installed_after = _collect_recursive_files(cmake_install_prefix)
            cmake_manifest = sorted(installed_after - installed_before)

        process_manifest = getattr(dist, "cmake_process_manifest_hook", None)
        processed_manifest = _process_manifest(cmake_manifest, process_manifest)
        _prune_manifest(cmake_install_prefix, cmake_manifest, processed_manifest)
        self._record_installed_files(
            build_temp, cmake_install_prefix, processed_manifest
        )
        if use_wrapper_classic_layout_compat:
            self._apply_wrapper_classic_layout_compat(
                staged_install_dir=cmake_install_prefix, install_subdir=install_subdir
            )

    def get_outputs(self) -> list[str]:
        if self.editable_mode:
            return sorted(self.get_output_mapping())
        return sorted(os.fspath(path) for path in self._installed_files)

    # def "get_source_file"(self) -> list[str]:
    #    return ["CMakeLists.txt"]

    def get_output_mapping(self) -> dict[str, str]:
        if (
            not self.editable_mode
            or self._editable_install_dir is None
            or self.build_lib is None
        ):
            return {}

        project_root = Path.cwd().resolve()
        mapping: dict[str, str] = {}
        for path in self._installed_files:
            try:
                relative_output = path.relative_to(self._editable_install_dir)
                relative_source = path.relative_to(project_root)
            except ValueError:
                continue

            mapping[os.fspath(Path(self.build_lib, relative_output))] = os.fspath(
                relative_source
            )

        return mapping


def _has_cmake(dist: Distribution) -> bool:
    build_cmake = dist.get_command_obj("build_cmake")
    assert isinstance(build_cmake, BuildCMake)
    return (
        build_cmake.source_dir is not None
        or getattr(dist, "cmake_source_dir", None) is not None
    )


def finalize_distribution_options(dist: Distribution) -> None:
    # Prepare new build_cmake command and make sure build calls it
    build = dist.get_command_class("build")
    assert build is not None
    if "build_cmake" not in {x for x, _ in build.sub_commands}:
        build.sub_commands.append(
            ("build_cmake", lambda cmd: _has_cmake(cmd.distribution))
        )

    # Direct "setup.py build_ext --inplace" invocations don't go through the
    # build command, so hook build_ext as well (run_command is a no-op if
    # build_cmake already ran).
    build_ext = dist.get_command_class("build_ext")
    assert build_ext is not None
    if not getattr(build_ext, "_scikit_build_core_patched", False):

        class BuildExtWithCMake(build_ext):  # type: ignore[valid-type,misc]
            _scikit_build_core_patched = True

            def run(self) -> None:
                if _has_cmake(self.distribution):
                    self.run_command("build_cmake")
                super().run()

        dist.cmdclass["build_ext"] = BuildExtWithCMake

    if get_source_dir_from_pyproject_toml() is not None:
        _cmake_extension(dist)


def _cmake_extension(dist: Distribution) -> None:
    # Every keyword argument needs to call this
    # Run this only once
    if getattr(dist, "_has_cmake_extensions", False):
        return

    # pylint: disable-next=protected-access
    dist._has_cmake_extensions = True  # type: ignore[attr-defined]

    # Setuptools needs to know that it has extensions modules
    orig_has_ext_modules = dist.has_ext_modules
    dist.has_ext_modules = lambda: orig_has_ext_modules() or _has_cmake(dist)  # type: ignore[method-assign]

    # Hack for stdlib distutils
    if not setuptools.distutils.__package__.startswith("setuptools"):  # type: ignore[attr-defined]

        class EvilList(list):  # type: ignore[type-arg]
            def __len__(self) -> int:
                return super().__len__() or int(_has_cmake(dist))

        dist.ext_modules = getattr(dist, "ext_modules", []) or EvilList()

    # Setup logging
    settings = _load_settings()
    level_value = LEVEL_VALUE[settings.logging.level]
    raw_logger.setLevel(level_value)


def cmake_args(
    dist: Distribution, attr: Literal["cmake_args"], value: list[str]
) -> None:
    assert attr == "cmake_args"
    _cmake_extension(dist)
    if not isinstance(value, list):
        msg = "cmake_args must be a list"
        raise SetupError(msg)


def cmake_install_dir(
    dist: Distribution, attr: Literal["cmake_install_dir"], value: str
) -> None:
    assert attr == "cmake_install_dir"
    _cmake_extension(dist)
    if not isinstance(value, str):
        msg = "cmake_install_dir must be a string"
        raise SetupError(msg)
    # Reject path traversal and drive components to prevent escaping build_lib
    p = Path(value)
    if p.is_absolute() or ".." in p.parts or p.drive:
        msg = f"cmake_install_dir must be a relative path without '..' components, got: {value!r}"
        raise SetupError(msg)


def cmake_source_dir(
    dist: Distribution, attr: Literal["cmake_source_dir"], value: str
) -> None:
    assert attr == "cmake_source_dir"
    if get_source_dir_from_pyproject_toml() is not None:
        msg = "cmake_source_dir is already defined in pyproject.toml"
        raise SetupError(msg)
    _cmake_extension(dist)
    if not Path(value).is_dir():
        msg = "cmake_source_dir must be an existing directory"
        raise SetupError(msg)


def cmake_install_target(
    dist: Distribution, attr: Literal["cmake_install_target"], value: str
) -> None:
    assert attr == "cmake_install_target"
    _cmake_extension(dist)
    if not isinstance(value, str):
        msg = "cmake_install_target must be a string"
        raise SetupError(msg)


def cmake_with_sdist(
    _dist: Distribution,
    attr: Literal["cmake_with_sdist"],
    value: bool,  # noqa: FBT001
) -> None:
    assert attr == "cmake_with_sdist"
    if value:
        msg = "cmake_with_sdist must not be set to True"
        raise SetupError(msg)


def cmake_process_manifest_hook(
    dist: Distribution,
    attr: Literal["cmake_process_manifest_hook"],
    value: Callable[[list[str]], list[str]] | None,
) -> None:
    assert attr == "cmake_process_manifest_hook"
    _cmake_extension(dist)
    if value is not None and not callable(value):
        msg = "cmake_process_manifest_hook must be callable"
        raise SetupError(msg)
