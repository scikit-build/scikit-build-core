from __future__ import annotations

import sys

from hatchling.builders.hooks.plugin.interface import BuildHookInterface

__all__ = ["ScikitBuildBuildHook"]


def __dir__() -> list[str]:
    return __all__


class ScikitBuildBuildHook(BuildHookInterface):  # type: ignore[misc]
    PLUGIN_NAME = "scikit_build_core"

    def __init__(self, *args: object, **kwargs: object) -> None:
        super().__init__(*args, **kwargs)

        self.__compiled_extension = ".pyd" if sys.platform.endswith("win") else ".so"
        self.__config_options: dict[str, object] | None = None

    @property
    def compiled_extension(self):
        return self.__compiled_extension

    @property
    def config_options(self) -> dict[str, object]:
        if self.__config_options is None:
            options = self.config.get("options", {})
            if not isinstance(options, dict):
                raise TypeError(
                    f"Option `options` for build hook `{self.PLUGIN_NAME}` must be a table"
                )

            self.__config_options = options

        return self.__config_options

    def initialize(self, version, build_data):
        if self.target_name != "wheel":
            return
