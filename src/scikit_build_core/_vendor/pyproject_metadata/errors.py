from __future__ import annotations

import builtins
import contextlib
import dataclasses
import sys
import typing

import packaging.specifiers
import packaging.version


__all__ = [
    'ConfigurationError',
    'ConfigurationWarning',
    'ExceptionGroup',
    'ErrorCollector',
]


def __dir__() -> list[str]:
    return __all__


class ConfigurationError(Exception):
    """Error in the backend metadata."""

    def __init__(self, msg: str, *, key: str | None = None):
        super().__init__(msg)
        self._key = key

    @property
    def key(self) -> str | None:  # pragma: no cover
        return self._key


class ConfigurationWarning(UserWarning):
    """Warnings about backend metadata."""


if sys.version_info >= (3, 11):
    ExceptionGroup = builtins.ExceptionGroup
else:

    class ExceptionGroup(Exception):
        """A minimal implementation of `ExceptionGroup` from Python 3.11."""

        message: str
        exceptions: list[Exception]

        def __init__(self, message: str, exceptions: list[Exception]) -> None:
            self.message = message
            self.exceptions = exceptions

        def __repr__(self) -> str:
            return f'{self.__class__.__name__}({self.message!r}, {self.exceptions!r})'


@dataclasses.dataclass
class ErrorCollector:
    collect_errors: bool
    errors: list[Exception] = dataclasses.field(default_factory=list)

    def config_error(self, msg: str, key: str | None = None) -> None:
        """Raise a configuration error, or add it to the error list."""
        if self.collect_errors:
            self.errors.append(ConfigurationError(msg, key=key))
        else:
            raise ConfigurationError(msg, key=key)

    def finalize(self, msg: str) -> None:
        """Raise a group exception if there are any errors."""
        if self.errors:
            raise ExceptionGroup(msg, self.errors)

    @contextlib.contextmanager
    def collect(self) -> typing.Generator[None, None, None]:
        if self.collect_errors:
            try:
                yield
            except (
                ConfigurationError,
                packaging.version.InvalidVersion,
                packaging.specifiers.InvalidSpecifier,
            ) as error:
                self.errors.append(error)
            except ExceptionGroup as error:
                self.errors.extend(error.exceptions)
        else:
            yield
