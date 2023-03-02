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
    env: dict[str, str] | None = None
    cwd: os.PathLike[str] | None = None

    def live(self, *args: str | os.PathLike[str]) -> None:
        """
        Runs code and prints the results live.
        """
        self._run(args, capture=False)

    def capture(
        self, *args: str | os.PathLike[str]
    ) -> subprocess.CompletedProcess[str]:
        """
        Runs a command and captures the result.
        """
        return self._run(args, capture=True)

    def _run(
        self,
        args: Iterable[str | os.PathLike[str]],
        capture: bool,
    ) -> subprocess.CompletedProcess[str]:
        options = [
            os.fspath(arg) if isinstance(arg, os.PathLike) else arg for arg in args
        ]

        if self.env:
            logger.debug(
                "RUNENV:\n  {}", "\n  ".join(f"{k}={v}" for k, v in self.env.items())
            )
        logger.debug("RUN: {}", " ".join(options))

        return subprocess.run(
            options,
            text=True,
            check=True,
            capture_output=capture,
            env=self.env,
            cwd=self.cwd,
        )
