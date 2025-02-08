from __future__ import annotations

import dataclasses
import os
import stat
import subprocess
from typing import TYPE_CHECKING, ClassVar

from ._logging import logger

if TYPE_CHECKING:
    from collections.abc import Iterable

__all__ = ["Run"]


def __dir__() -> list[str]:
    return __all__


@dataclasses.dataclass
class Run:
    env: dict[str, str] | None = None
    cwd: os.PathLike[str] | None = None
    timeout: None | float = None

    # Stores last printout, for cleaner debug logging
    _prev_env: ClassVar[dict[str, str]] = {}

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
        *,
        capture: bool,
    ) -> subprocess.CompletedProcess[str]:
        options = [
            os.fspath(arg) if isinstance(arg, os.PathLike) else arg for arg in args
        ]

        if self.env:
            if not self._prev_env:
                type(self)._prev_env = self.env.copy()
                msg = "\n  ".join(f"{k}={v!r}" for k, v in sorted(self.env.items()))
                logger.debug("RUNENV:\n  {}", msg)
            else:
                msg = "\n  ".join(
                    f"{self._key_diff(k)} {k}={self.env.get(k, '<unset>')!r}"
                    for k in sorted(self.env.keys() | self._prev_env.keys())
                    if self._prev_env.get(k, None) != self.env.get(k, None)
                )
                logger.debug("RUNENV - changes since last run only:\n  {}", msg)
                type(self)._prev_env = self.env.copy()

        logger.info("RUN: {}", " ".join(options))

        return subprocess.run(
            options,
            text=True,
            check=True,
            capture_output=capture,
            env=self.env,
            cwd=self.cwd,
            timeout=self.timeout,
        )

    def _key_diff(self, k: str) -> str:
        assert self.env
        if k in self.env and k not in self._prev_env:
            return "+"
        if k in self._prev_env and k not in self.env:
            return "-"
        return " "


def _fix_all_permissions(directory: str) -> None:
    """
    Makes sure the write permission is set. Only run this on Windows.
    """
    with os.scandir(directory) as it:
        for entry in it:
            if entry.is_dir():
                _fix_all_permissions(entry.path)
                continue
            mode = stat.S_IMODE(entry.stat().st_mode)
            if not mode & stat.S_IWRITE:
                os.chmod(entry.path, mode | stat.S_IWRITE)  # noqa: PTH101
