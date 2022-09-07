from __future__ import annotations

import dataclasses
import os
import subprocess
from collections.abc import Iterable

from ._logging import logger

__all__ = ["Run"]


def __dir__() -> list[str]:
    return __all__


@dataclasses.dataclass
class Run:
    env: dict[str, str | os.PathLike[str]] | None = None
    cwd: os.PathLike[str] | None = None

    def live(
        self, *args: str | os.PathLike[str], **kwargs: str | os.PathLike[str]
    ) -> None:
        """
        Runs code and prints the results live.
        """
        self._run(args, kwargs, capture=False)

    def capture(
        self, *args: str | os.PathLike[str], **kwargs: str | os.PathLike[str]
    ) -> subprocess.CompletedProcess[str]:
        """
        Runs a command and captures the result.
        """
        return self._run(args, kwargs, capture=True)

    def _run(
        self,
        args: Iterable[str | os.PathLike[str]],
        kwargs: dict[str, str | os.PathLike[str]],
        capture: bool,
    ) -> subprocess.CompletedProcess[str]:
        # Flatten {a=b, c=d} into [--a, b, --c, d] as a flat list.
        kw_options = [
            item for key, value in kwargs.items() for item in (f"--{key}", f"{value}")
        ]
        options = [
            os.fspath(arg) if isinstance(arg, os.PathLike) else arg for arg in args
        ] + kw_options

        logger.debug("RUN: {}", " ".join(options))

        if capture:
            return subprocess.run(
                options,
                text=True,
                check=True,
                capture_output=True,
            )
        return subprocess.run(
            options,
            check=True,
            text=True,
        )
