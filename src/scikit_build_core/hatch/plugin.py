from __future__ import annotations

import copy
import os
import typing
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any

from hatchling.builders.hooks.plugin.interface import BuildHookInterface

from .._compat.typing import Literal
from ..build._init import setup_logging
from ..builder.builder import Builder, archs_to_tags, get_archs
from ..builder.get_requires import GetRequires
from ..builder.wheel_tag import WheelTag
from ..cmake import CMake, CMaker
from ..settings.skbuild_read_settings import SettingsReader

# from ..settings.metadata import get_standard_metadata

__all__ = ["ScikitBuildHook"]


def __dir__() -> list[str]:
    return __all__


class ScikitBuildHook(BuildHookInterface):  # type: ignore[type-arg]
    PLUGIN_NAME = "scikit-build"

    def _read_config(self) -> SettingsReader:
        config_dict = copy.deepcopy(self.config)
        config_dict.pop("dependencies", None)

        state = typing.cast(Literal["sdist", "wheel", "editable"], self.target_name)
        return SettingsReader.from_file(
            "pyproject.toml", state=state, extra_settings=config_dict
        )

    def dependencies(self) -> list[str]:
        settings = self._read_config().settings
        requires = GetRequires(settings)

        if self.target_name == "sdist":
            required = requires.settings.sdist.cmake
        elif self.target_name in {"wheel", "editable"}:
            required = requires.settings.wheel.cmake
        else:
            msg = f"Unknown target: {self.target_name!r}, only 'sdist', 'wheel', 'editable' are supported"
            raise ValueError(msg)

        # These are only injected if cmake is required
        cmake_requires = [*requires.cmake(), *requires.ninja()] if required else []
        return [*cmake_requires, *requires.dynamic_metadata()]

    def initialize(self, version: str, build_data: dict[str, Any]) -> None:  # noqa: ARG002
        settings_reader = self._read_config()
        settings = settings_reader.settings

        setup_logging(settings.logging.level)

        if not settings.wheel.cmake or settings.sdist.cmake:
            msg = "CMake is required for scikit-build"
            raise ValueError(msg)

        cmake = CMake.default_search(version=settings.cmake.version, env=os.environ)

        settings_reader.validate_may_exit()

        # metadata = get_standard_metadata(pyproject, settings)

        if self.target_name == "sdist":
            if (
                settings.sdist.include
                or settings.sdist.exclude
                or settings.sdist.reproducible
            ):
                msg = "include, exclude, and reproducible are not supported for hatch builds"
                raise ValueError(msg)

            if settings.sdist.cmake:
                msg = "Not currently supported for SDist builds"
                raise ValueError(msg)

            build_data["artifacts"].append("CMakeLists.txt")  # Needs full list, etc.
            return

        tags = WheelTag.compute_best(
            archs_to_tags(get_archs(os.environ)),
            settings.wheel.py_api,
            expand_macos=settings.wheel.expand_macos_universal_tags,
            build_tag=settings.wheel.build_tag,
        )
        build_data["tag"] = str(tags)

        # if settings.wheel.packages or settings.wheel.license_files:
        #     msg = ""
        #     raise ValueError(msg)

        # if settings.wheel.cmake:
        #     msg = "Not currently supported for wheel builds"
        #     raise ValueError(msg)

        source_dir = Path.cwd() / settings.cmake.source_dir

        build_dir = Path(TemporaryDirectory().name)
        if settings.build_dir:
            build_dir = Path.cwd() / settings.build_dir

        if settings.wheel.platlib is not None and not settings.wheel.platlib:
            msg = "Purelib builds not supported for hatch builds"
            raise ValueError(msg)

        targetlib = "platlib"

        # prefix = Path.cwd() / "prefix"
        if settings.wheel.install_dir:
            prefix = Path.cwd() / targetlib / settings.wheel.install_dir
        else:
            prefix = Path.cwd() / targetlib

        config = CMaker(
            cmake,
            source_dir=source_dir,
            build_dir=build_dir,
            build_type=settings.cmake.build_type,
        )

        builder = Builder(settings, config)

        # cache_entries: dict[str, str | Path] = {
        #                 f"SKBUILD_{k.upper()}_DIR": v for k, v in wheel_dirs.items()
        # }
        # cache_entries["SKBUILD_STATE"] = self.target_name

        builder.configure(
            defines={},
            # cache_entries=cache_entries,
            # name=metadata.name,
            # version=metadata.version
        )
        builder.build([])
        builder.install(prefix)

        for path in prefix.iterdir():
            build_data["artifacts"].append(path)
            build_data["force_include"][
                f"{targetlib}/{settings.wheel.install_dir}/{path.relative_to(prefix)}"
            ] = str(settings.wheel.install_dir / path.relative_to(prefix))

        build_data["pure_python"] = not settings.wheel.platlib
