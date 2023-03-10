from __future__ import annotations

import dataclasses
import itertools
import sys
from collections.abc import Iterable, Sequence

import packaging.tags

from .._compat.typing import Self
from .._logging import logger
from .macos import get_macosx_deployment_target

__all__ = ["WheelTag"]


def __dir__() -> list[str]:
    return __all__


@dataclasses.dataclass(frozen=True)
class WheelTag:
    pyvers: list[str]
    abis: list[str]
    archs: list[str]

    # TODO: plats only used on macOS & Windows
    @classmethod
    def compute_best(
        cls,
        archs: Sequence[str],
        py_api: str = "",
        expand_macos: bool = False,
    ) -> Self:
        best_tag = next(packaging.tags.sys_tags())
        interp, abi, *plats = (best_tag.interpreter, best_tag.abi, best_tag.platform)
        pyvers = [interp]

        if sys.platform.startswith("win") and archs:
            plats = [x.replace("-", "_") for x in archs]
        elif sys.platform.startswith("darwin"):
            pairs: Iterable[tuple[str | None, bool]]
            if expand_macos and archs == ["universal2"]:
                pairs = zip(
                    ["universal2", "universal2", "x86_64", "arm64"],
                    [False, True, False, True],
                )
            elif not archs:
                # It's okay to set arm to False, since this would be a native build,
                # and that will already be 11+ for ARM anyway.
                pairs = zip([None], [False])
            else:
                pairs = zip(archs, [a == "arm64" for a in archs])
            plats = [
                next(
                    packaging.tags.mac_platforms(
                        get_macosx_deployment_target(arm), arch
                    )
                )
                for arch, arm in pairs
            ]
            # Remove duplicates (e.g. universal2 if macOS > 11.0 and expanded)
            plats = list(dict.fromkeys(plats))

        if py_api:
            pyvers_new = py_api.split(".")
            if all(x.startswith("cp3") and x[3:].isdecimal() for x in pyvers_new):
                if len(pyvers_new) != 1:
                    msg = "Unexpected py-api, must be a single cp version (e.g. cp39), not {py_api}"
                    raise AssertionError(msg)
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
                msg = f"Unexpected py-api, must be abi3 (e.g. cp39) or Pythonless (e.g. py2.py3), not {py_api}"
                raise AssertionError(msg)

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

    def as_tags_set(self) -> frozenset[packaging.tags.Tag]:
        vals = itertools.product(self.pyvers, self.abis, self.archs)
        return frozenset(packaging.tags.Tag(*v) for v in vals)


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
