from __future__ import annotations

import dataclasses
import sys
from collections.abc import Sequence
from typing import TypeVar

import packaging.tags

from .._logging import logger
from .macos import get_macosx_deployment_target

__all__ = ["WheelTag"]


def __dir__() -> list[str]:
    return __all__


Self = TypeVar("Self", bound="WheelTag")


@dataclasses.dataclass(frozen=True)
class WheelTag:
    pyvers: list[str]
    abis: list[str]
    archs: list[str]

    # TODO: plats only used on macOS
    @classmethod
    def compute_best(
        cls: type[Self], archs: Sequence[str] = (), py_api: str = ""
    ) -> Self:
        best_tag = next(packaging.tags.sys_tags())
        interp, abi, *plats = (best_tag.interpreter, best_tag.abi, best_tag.platform)
        pyvers = [interp]
        if sys.platform.startswith("darwin"):
            major, minor = get_macosx_deployment_target(archs == ["arm64"])
            if archs:
                plats = [
                    next(packaging.tags.mac_platforms((major, minor), arch))
                    for arch in archs
                ]
            else:
                plats = [next(packaging.tags.mac_platforms((major, minor)))]

        if py_api:
            pyvers_new = py_api.split(".")
            if all(x.startswith("cp3") and x[3:].isdecimal() for x in pyvers_new):
                if len(pyvers_new) != 1:
                    raise AssertionError(
                        "Unexpected py-api, must be a single cp version (e.g. cp39)"
                    )
                minor = int(pyvers_new[0][3:])
                if (
                    sys.implementation.name == "cpython"
                    and minor <= sys.version_info.minor
                ):
                    pyvers = pyvers_new
                    abi = "abi3"
                else:
                    msg = "Ignoring py-api, not a CPython interpreter ({}) or version (3.{}) is too high"
                    logger.debug(msg, sys.implementation.name, minor)
            elif all(x.startswith("py") and x[2:].isdecimal() for x in pyvers_new):
                pyvers = pyvers_new
                abi = "none"
            else:
                raise AssertionError(
                    "Unexpected py-api, must be abi3 (e.g. cp39) or Pythonless (e.g. py2.py3)"
                )

        return cls(pyvers=pyvers, abis=[abi], archs=plats)

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


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--archs",
        nargs="*",
        default=[],
        help="Specify one or more archs (macOS only currently)",
    )
    parser.add_argument(
        "--abi",
        default="",
        help="Specify py-api, like 'cp37' or 'py3'",
    )
    args = parser.parse_args()
    tag = WheelTag.compute_best(args.archs, args.abi)
    print(tag)  # noqa: T201
