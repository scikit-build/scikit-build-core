from __future__ import annotations

import contextlib
import dataclasses
import json
import os
import shutil
import subprocess
import sys
import sysconfig
import textwrap
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Generator

from packaging.version import Version

from . import __version__
from ._compat.typing import Self
from ._logging import logger
from ._shutil import Run
from .errors import CMakeConfigError, CMakeNotFoundError, FailedLiveProcessError
from .program_search import best_program, get_cmake_programs

__all__ = ["CMake", "CMaker"]


def __dir__() -> list[str]:
    return __all__


DIR = Path(__file__).parent.resolve()


@dataclasses.dataclass(frozen=True)
class CMake:
    version: Version
    cmake_path: Path

    @classmethod
    def default_search(
        cls, *, minimum_version: Version | None = None, module: bool = True
    ) -> Self:
        candidates = get_cmake_programs(module=module)
        cmake_program = best_program(candidates, minimum_version=minimum_version)

        if cmake_program is None:
            msg = f"Could not find CMake with version >= {minimum_version}"
            raise CMakeNotFoundError(msg)
        if cmake_program.version is None:
            msg = "CMake version undetermined @ {program.path}"
            raise CMakeNotFoundError(msg)

        return cls(version=cmake_program.version, cmake_path=cmake_program.path)

    def __fspath__(self) -> str:
        return os.fspath(self.cmake_path)


@dataclasses.dataclass
class CMaker:
    cmake: CMake
    source_dir: Path
    build_dir: Path
    build_type: str
    module_dirs: list[Path] = dataclasses.field(default_factory=list)
    prefix_dirs: list[Path] = dataclasses.field(default_factory=list)
    init_cache_file: Path = dataclasses.field(init=False, default=Path())
    env: dict[str, str] = dataclasses.field(init=False, default_factory=os.environ.copy)
    single_config: bool = not sysconfig.get_platform().startswith("win")

    def __post_init__(self) -> None:
        self.init_cache_file = self.build_dir / "CMakeInit.txt"

        if not self.source_dir.is_dir():
            msg = f"source directory {self.source_dir} does not exist"
            raise CMakeConfigError(msg)

        self.build_dir.mkdir(parents=True, exist_ok=True)
        if not self.build_dir.is_dir():
            msg = f"build directory {self.build_dir} must be a (creatable) directory"
            raise CMakeConfigError(msg)

        # If these were the same, the following check could wipe the source directory!
        if self.build_dir.resolve() == self.source_dir.resolve():
            msg = "build directory must be different from source directory"
            raise CMakeConfigError(msg)

        skbuild_info = self.build_dir / ".skbuild-info.json"
        # If building via SDist, this could be pre-filled, so delete it if it exists
        with contextlib.suppress(FileNotFoundError):
            with skbuild_info.open("r", encoding="utf-8") as f:
                info = json.load(f)

            cached_source_dir = Path(info["source_dir"])
            if cached_source_dir.resolve() != self.source_dir.resolve():
                logger.warning(
                    "Original src {} != {}, wiping build directory",
                    cached_source_dir,
                    self.source_dir,
                )
                shutil.rmtree(self.build_dir)
                self.build_dir.mkdir()

        with skbuild_info.open("w", encoding="utf-8") as f:
            json.dump(self._info_dict(), f, indent=2)

    def _info_dict(self) -> dict[str, str]:
        """
        Produce an information dict about the current run that can be stored in a json file.
        """
        return {
            "source_dir": os.fspath(self.source_dir.resolve()),
            "build_dir": os.fspath(self.build_dir.resolve()),
            "cmake_path": os.fspath(self.cmake),
            "skbuild_path": os.fspath(DIR),
            "skbuild_version": __version__,
            "python_executable": sys.executable,
        }

    def init_cache(
        self, cache_settings: Mapping[str, str | os.PathLike[str] | bool]
    ) -> None:
        with self.init_cache_file.open("w", encoding="utf-8") as f:
            for key, value in cache_settings.items():
                if isinstance(value, bool):
                    str_value = "ON" if value else "OFF"
                    f.write(f'set({key} {str_value} CACHE BOOL "" FORCE)\n')
                elif isinstance(value, os.PathLike):
                    # Convert to CMake's internal path format
                    str_value = str(value).replace("\\", "/")
                    f.write(f'set({key} [===[{str_value}]===] CACHE PATH "" FORCE)\n')
                else:
                    f.write(f'set({key} [===[{value}]===] CACHE STRING "" FORCE)\n')

            if self.module_dirs:
                # Convert to CMake's internal path format, otherwise this breaks try_compile on Windows
                module_dirs_str = ";".join(map(str, self.module_dirs)).replace(
                    "\\", "/"
                )
                f.write(
                    f'set(CMAKE_MODULE_PATH [===[{module_dirs_str}]===] CACHE PATH "" FORCE)\n'
                )

            if self.prefix_dirs:
                prefix_dirs_str = ";".join(map(str, self.prefix_dirs)).replace(
                    "\\", "/"
                )
                f.write(
                    f'set(CMAKE_PREFIX_PATH [===[{prefix_dirs_str}]===] CACHE PATH "" FORCE)\n'
                )
                f.write('set(CMAKE_FIND_ROOT_PATH_MODE_PACKAGE "BOTH" CACHE PATH "")\n')

        contents = self.init_cache_file.read_text(encoding="utf-8").strip()
        logger.debug(
            "{}:\n{}",
            self.init_cache_file,
            textwrap.indent(contents.strip(), "  "),
        )

    def _compute_cmake_args(
        self, defines: Mapping[str, str | os.PathLike[str] | bool]
    ) -> Generator[str, None, None]:
        yield f"-S{self.source_dir}"
        yield f"-B{self.build_dir}"

        if self.init_cache_file.is_file():
            yield f"-C{self.init_cache_file}"

        if self.single_config and self.build_type:
            yield f"-DCMAKE_BUILD_TYPE:STRING={self.build_type}"

        for key, value in defines.items():
            if isinstance(value, bool):
                str_value = "ON" if value else "OFF"
                yield f"-D{key}:BOOL={str_value}"
            elif isinstance(value, os.PathLike):
                str_value = str(value).replace("\\", "/")
                yield f"-D{key}:PATH={str_value}"
            else:
                yield f"-D{key}={value}"

    def configure(
        self,
        *,
        defines: Mapping[str, str | os.PathLike[str] | bool] | None = None,
        cmake_args: Sequence[str] = (),
    ) -> None:
        if "CMAKE_GENERATOR" in self.env:
            gen = self.env["CMAKE_GENERATOR"]
            self.single_config = gen == "Ninja" or "Makefiles" in gen

        _cmake_args = self._compute_cmake_args(defines or {})

        try:
            Run(env=self.env).live(self.cmake, *_cmake_args, *cmake_args)
        except subprocess.CalledProcessError:
            msg = "CMake configuration failed"
            raise FailedLiveProcessError(msg) from None

    def _compute_build_args(
        self,
        *,
        verbose: bool,
    ) -> Generator[str, None, None]:
        if verbose:
            yield "-v"
        if self.build_type and not self.single_config:
            yield "--config"
            yield self.build_type

    def build(self, build_args: Sequence[str] = (), *, verbose: bool = False) -> None:
        local_args = self._compute_build_args(verbose=verbose)

        try:
            Run(env=self.env).live(
                self.cmake, "--build", self.build_dir, *build_args, *local_args
            )
        except subprocess.CalledProcessError:
            msg = "CMake build failed"
            raise FailedLiveProcessError(msg) from None

    def install(self, prefix: Path) -> None:
        opts: list[str] = []
        if not self.single_config and self.build_type:
            opts += ["--config", self.build_type]
        try:
            Run(env=self.env).live(
                self.cmake,
                "--install",
                self.build_dir,
                "--prefix",
                prefix,
                *opts,
            )
        except subprocess.CalledProcessError:
            msg = "CMake install failed"
            raise FailedLiveProcessError(msg) from None
