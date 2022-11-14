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
        cls: type[Self], archs: Sequence[str] = (), api_abi: str = ""
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

        if api_abi:
            pyver_new, abi_new = api_abi.split("-")
            pyvers_new = pyver_new.split(".")
            if all(x.startswith("cp") for x in pyvers_new) and abi_new == "abi3":
                if len(pyvers_new) > 1:
                    raise AssertionError(
                        "Unexpected api-abi, must be a single cp version (e.g. cp39)"
                    )
                minor = int(pyvers_new[0][3:])
                if (
                    sys.implementation.name == "cpython"
                    and minor <= sys.version_info.minor
                ):
                    pyvers = pyvers_new
                    abi = abi_new
                else:
                    msg = "Ignoring api-abi, not a CPython interpreter ({}) or version (3.{}) is too high"
                    logger.debug(msg, sys.implementation.name, minor)
            elif all(x.startswith("py") for x in pyvers_new) and abi_new == "none":
                pyvers = pyvers_new
                abi = abi_new
            else:
                raise AssertionError(
                    "Unexpected api-abi, must be abi3 (e.g. cp39-abi3) or Pythonless (e.g. py2.py3-none)"
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
        help="Specify api-abi, like 'cp37-abi3' or 'py3-none'",
    )
    args = parser.parse_args()
    tag = WheelTag.compute_best(args.archs, args.abi)
    print(tag)  # noqa: T201
