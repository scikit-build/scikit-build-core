from __future__ import annotations

import copy
import os
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any

from hatchling.builders.hooks.plugin.interface import BuildHookInterface

from .._compat import tomllib
from ..builder.builder import Builder
from ..cmake import CMake, CMaker
from ..settings.skbuild_read_settings import SettingsReader

__all__ = ["ScikitBuildHook"]


def __dir__() -> list[str]:
    return __all__


class ScikitBuildHook(BuildHookInterface):  # type: ignore[type-arg]
    PLUGIN_NAME = "scikit-build"

    def initialize(self, version: str, build_data: dict[str, Any]) -> None:  # noqa: ARG002
        if self.target_name == "sdist":
            build_data["artifacts"].append("CMakeLists.txt")  # Needs full list, etc.
            return

        pyproject_path = Path("pyproject.toml")
        with pyproject_path.open("rb") as ft:
            pyproject = tomllib.load(ft)

        config_dict = copy.deepcopy(self.config)

        config_dict.pop("dependencies", None)

        settings_reader = SettingsReader(
            pyproject, {}, state=self.target_name, extra_settings=config_dict
        )
        settings = settings_reader.settings

        if not settings.wheel.cmake:
            msg = "CMake is required for scikit-build"
            raise ValueError(msg)

        cmake = CMake.default_search(version=settings.cmake.version, env=os.environ)

        settings_reader.validate_may_exit()

        source_dir = Path.cwd()
        if settings.cmake.source_dir:
            print(f"source-dir: {settings.cmake.source_dir}")
            source_dir = Path.cwd() / settings.cmake.source_dir

        build_dir = Path(TemporaryDirectory().name)
        if settings.build_dir:
            print(f"build-dir: {settings.build_dir}")
            build_dir = Path.cwd() / settings.build_dir

        prefix = Path.cwd() / "prefix"

        config = CMaker(
            cmake,
            source_dir=source_dir,
            build_dir=build_dir,
            build_type=settings.cmake.build_type,
        )

        builder = Builder(settings, config)
        builder.configure(defines={})
        builder.build([])
        builder.install(prefix)

        for path in prefix.iterdir():
            build_data["artifacts"].append(path)
            build_data["force_include"][f"prefix/{path.relative_to(prefix)}"] = str(
                settings.wheel.install_dir / path.relative_to(prefix)
            )

        build_data["infer_tag"] = True
        build_data["pure_python"] = False
