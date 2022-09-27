from __future__ import annotations

import dataclasses
import os
import sys
from pathlib import Path
from typing import Any, TypeVar, Union

if sys.version_info < (3, 11):
    from exceptiongroup import ExceptionGroup

if sys.version_info >= (3, 8):
    from typing import Protocol
else:
    from typing_extensions import Protocol


T = TypeVar("T")


def _dig(dict_: dict[str, Any], *names: str) -> Any:
    for name in names:
        dict_ = dict_[name]
    return dict_


class Source(Protocol):
    def has_item(self, *fields: str) -> Source | None:
        """
        Check if the source contains a chain of fields. For example, feilds =
        [Field(name="a"), Field(name="b")] will check if the source contains the
        key "a.b". Returns the first source that contains the field (possibly
        self).
        """
        ...

    def get_item(self, *fields: str) -> Any:
        ...

    @classmethod
    def convert(cls, item: Any, target: type[T]) -> T:
        ...


class EnvSource:
    """
    This is a source using environment variables.
    """

    def __init__(self, prefix: str, *, env: dict[str, str] | None = None) -> None:
        self.env = env or os.environ
        self.prefix = prefix

    def _get_name(self, *fields: str) -> str:
        names = [field.upper() for field in fields]
        return "_".join([self.prefix, *names] if self.prefix else names)

    def has_item(self, *fields: str) -> EnvSource | None:
        name = self._get_name(*fields)
        return self if name in self.env else None

    def get_item(self, *fields: str) -> str:
        name = self._get_name(*fields)
        if name in self.env:
            return self.env[name]
        raise KeyError(f"{name!r} not found in environment")

    @classmethod
    def convert(cls, item: str, target: type[T]) -> T:
        if hasattr(target, "__origin__"):
            if target.__origin__ == list:  # type: ignore[attr-defined]
                return [cls.convert(i, target.__args__[0]) for i in item.split(";")]  # type: ignore[return-value,attr-defined]
            if target.__origin__ == Union:  # type: ignore[attr-defined]
                return cls.convert(item, target.__args__[0])  # type: ignore[no-any-return,attr-defined]
        return target(item)  # type: ignore[call-arg]


class ConfSource:
    """
    This is a source for the PEP 517 configuration settings.
    You should initialize it with a dict from PEP 517. a.b will be treated as
    nested dicts.
    """

    def __init__(self, *prefixes: str, settings: dict[str, str | list[str]]):
        self.prefixes = prefixes
        self.settings = settings

    def _get_name(self, *fields: str) -> list[str]:
        names = [field.replace("_", "-") for field in fields]
        return [*self.prefixes, *names]

    def has_item(self, *fields: str) -> ConfSource | None:
        names = self._get_name(*fields)
        name = ".".join(names)

        return self if name in self.settings else None

    def get_item(self, *fields: str) -> str | list[str]:
        names = self._get_name(*fields)
        name = ".".join(names)
        if name in self.settings:
            return self.settings[name]

        raise KeyError(f"{name!r} not found in configuration settings")

    @classmethod
    def convert(cls, item: str | list[str], target: type[T]) -> T:
        if isinstance(item, list):
            return [cls.convert(i, target.__args__[0]) for i in item]  # type: ignore[return-value,attr-defined]
        if hasattr(target, "__origin__"):
            if target.__origin__ == Union:  # type: ignore[attr-defined]
                return cls.convert(item, target.__args__[0])  # type: ignore[no-any-return,attr-defined]
        return target(item)  # type: ignore[call-arg]


class TOMLSource:
    def __init__(self, *prefixes: str, settings: dict[str, Any]):
        self.prefixes = prefixes
        self.settings = settings

    def _get_name(self, *fields: str) -> list[str]:
        names = [field.replace("_", "-") for field in fields]
        return [*self.prefixes, *names]

    def has_item(self, *fields: str) -> TOMLSource | None:
        names = self._get_name(*fields)
        try:
            _dig(self.settings, *names)
            return self
        except KeyError:
            return None

    def get_item(self, *fields: str) -> Any:
        names = self._get_name(*fields)
        try:
            return _dig(self.settings, *names)
        except KeyError:
            raise KeyError(f"{names!r} not found in configuration settings") from None

    @classmethod
    def convert(cls, item: Any, target: type[T]) -> T:
        if isinstance(target, type) and issubclass(target, Path):  # type: ignore[redundant-expr]
            return target(item)  # type: ignore[return-value]
        return item  # type: ignore[no-any-return]


class SourceChain:
    def __init__(self, *sources: Source):
        self.sources = sources

    def has_item(self, *fields: str) -> Source | None:
        for source in self.sources:
            check = source.has_item(*fields)
            if check is not None:
                return check
        return None

    def get_item(self, *fields: str) -> Any:
        for source in self.sources:
            if source.has_item(*fields):
                return source.get_item(*fields)
        raise KeyError(f"{fields!r} not found in any source")

    @classmethod
    def convert(cls, item: Any, target: type[T]) -> T:
        raise NotImplementedError(
            "SourceChain cannot convert items, use the result from has_item"
        )

    def convert_target(self, target: type[T], *prefixes: str) -> T:
        errors = []
        prep = {}
        for field in dataclasses.fields(target):
            if dataclasses.is_dataclass(field.type):
                try:
                    prep[field.name] = self.convert_target(
                        field.type, *prefixes, field.name
                    )
                except Exception as e:
                    errors.append(e)
                continue

            local_source = self.has_item(*prefixes, field.name)
            if local_source is not None:
                simple = local_source.get_item(*prefixes, field.name)
                try:
                    prep[field.name] = local_source.convert(simple, field.type)
                except Exception as e:
                    errors.append(e)
                continue

            if field.default is not dataclasses.MISSING:
                prep[field.name] = field.default
                continue

            errors.append(ValueError(f"Missing value for {field.name!r}"))

        if errors:
            prefix_str = ".".join(prefixes)
            raise ExceptionGroup(f"Failed converting {prefix_str}", errors)

        return target(**prep)
