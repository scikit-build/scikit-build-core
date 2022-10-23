from __future__ import annotations

import dataclasses
import sys
from typing import TypeVar

import packaging.tags

from ..builder.macos import get_macosx_deployment_target

__all__ = ["WheelTag"]


def __dir__() -> list[str]:
    return __all__


Self = TypeVar("Self", bound="WheelTag")


@dataclasses.dataclass
class WheelTag:
    pyvers: list[str]
    abis: list[str]
    archs: list[str]

    @classmethod
    def compute_best(cls: type[Self]) -> Self:
        best_tag = next(packaging.tags.sys_tags())
        interp, abi, plat = (best_tag.interpreter, best_tag.abi, best_tag.platform)
        if sys.platform.startswith("darwin"):
            str_target = get_macosx_deployment_target()
            min_macos, max_macos = str_target.split(".")
            plat = next(packaging.tags.mac_platforms((int(min_macos), int(max_macos))))

        return cls(pyvers=[interp], abis=[abi], archs=[plat])

    @property
    def pyver(self) -> str:
        return ".".join(self.pyvers)

    @property
    def abi(self) -> str:
        return ".".join(self.abis)

    @property
    def arch(self) -> str:
        return ".".join(self.archs)

    def __str__(self) -> str:
        return f"{self.pyver}-{self.abi}-{self.arch}"

    def tags_dict(self) -> dict[str, list[str]]:
        return {
            "pyver": self.pyvers,
            "abi": self.abis,
            "arch": self.archs,
        }
