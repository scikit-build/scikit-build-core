from __future__ import annotations

import dataclasses
import os
from collections.abc import Generator, Mapping, Sequence
from typing import Any, TypeVar, Union

from .._compat.builtins import ExceptionGroup
from .._compat.typing import Protocol, runtime_checkable

T = TypeVar("T")

__all__ = ["Source", "SourceChain", "ConfSource", "EnvSource", "TOMLSource"]


def __dir__() -> list[str]:
    return __all__


def _dig_strict(dict_: Mapping[str, Any], *names: str) -> Any:
    for name in names:
        dict_ = dict_[name]
    return dict_


def _dig_not_strict(dict_: Mapping[str, Any], *names: str) -> Any:
    for name in names:
        dict_ = dict_.get(name, {})
    return dict_


@runtime_checkable
class TypeLike(Protocol):
    @property
    def __origin__(self) -> Any:
        ...

    @property
    def __args__(self) -> list[Any]:
        ...


def _process_union(target: TypeLike) -> Any:
    """
    Selects the non-None item in an Optional or Optional-like Union.
    """

    if len(target.__args__) == 2:
        items = list(target.__args__)
        if type(None) not in items:
            raise AssertionError(f"None must be in union, got {items}")
        items.remove(type(None))
        return items[0]

    raise AssertionError("Only Unions with None supported")


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
    def convert(cls, item: Any, target: object) -> object:
        ...

    def unrecognized_options(self, options: object) -> Generator[str, None, None]:
        ...


class EnvSource:
    """
    This is a source using environment variables.
    """

    def __init__(self, prefix: str, *, env: Mapping[str, str] | None = None) -> None:
        self.env = env or os.environ
        self.prefix = prefix

    def _get_name(self, *fields: str) -> str:
        names = [field.upper() for field in fields]
        return "_".join([self.prefix, *names] if self.prefix else names)

    def has_item(self, *fields: str) -> EnvSource | None:
        name = self._get_name(*fields)
        return self if name in self.env and self.env[name] else None

    def get_item(self, *fields: str) -> str:
        name = self._get_name(*fields)
        if name in self.env:
            return self.env[name]
        raise KeyError(f"{name!r} not found in environment")

    @classmethod
    def convert(cls, item: str, target: object) -> object:
        if isinstance(target, TypeLike) and hasattr(target, "__origin__"):
            if target.__origin__ == list:
                return [
                    cls.convert(i.strip(), target.__args__[0]) for i in item.split(";")
                ]
            if target.__origin__ == Union:
                return cls.convert(item, _process_union(target))
        if target is bool:
            result = item.strip().lower() not in {"0", "false", "off", "no", ""}
            return result
        if callable(target):
            return target(item)
        raise AssertionError(f"Can't convert target {target}")

    # pylint: disable-next=unused-argument
    def unrecognized_options(self, options: object) -> Generator[str, None, None]:
        yield from ()


def _unrecognized_dict(
    settings: Mapping[str, Any], options: object, above: Sequence[str]
) -> Generator[str, None, None]:
    for keystr in settings:
        matches = [
            x for x in dataclasses.fields(options) if x.name.replace("_", "-") == keystr
        ]
        if not matches:
            yield ".".join((*above, keystr))
            continue
        (inner_option_field,) = matches
        inner_option = inner_option_field.type
        if dataclasses.is_dataclass(inner_option):
            yield from _unrecognized_dict(
                settings[keystr], inner_option, (*above, keystr)
            )


class ConfSource:
    """
    This is a source for the PEP 517 configuration settings.
    You should initialize it with a dict from PEP 517. a.b will be treated as
    nested dicts. "verify" is a boolean that determines whether unrecognized
    options should be checked for. Only set this to false if this might be sharing
    config options at the same level.
    """

    def __init__(
        self,
        *prefixes: str,
        settings: Mapping[str, str | list[str]],
        verify: bool = True,
    ):
        self.prefixes = prefixes
        self.settings = settings
        self.verify = verify

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
    def convert(cls, item: str | list[str], target: object) -> object:
        # The hasattr is required for Python 3.7, though not quite sure why
        if isinstance(target, TypeLike) and hasattr(target, "__origin__"):
            if target.__origin__ == list:
                if isinstance(item, list):
                    return [cls.convert(i, target.__args__[0]) for i in item]
                return [
                    cls.convert(i.strip(), target.__args__[0]) for i in item.split(";")
                ]
            if target.__origin__ == Union:
                return cls.convert(item, _process_union(target))
        assert not isinstance(item, list), "Can't convert list to non-list"
        if target is bool:
            result = item.strip().lower() not in {"0", "false", "off", "no", ""}
            return result
        if callable(target):
            return target(item)
        raise AssertionError(f"Can't convert target {target}")

    def unrecognized_options(self, options: object) -> Generator[str, None, None]:
        if not self.verify:
            return
        for keystr in self.settings:
            inner_option = options
            keys = keystr.split(".")[len(self.prefixes) :]
            for i, key in enumerate(keys):
                matches = [
                    x
                    for x in dataclasses.fields(inner_option)
                    if x.name.replace("_", "-") == key
                ]
                if not matches:
                    yield ".".join(list(self.prefixes) + keys[: i + 1])
                    break
                (inner_option_field,) = matches
                inner_option = inner_option_field.type


class TOMLSource:
    def __init__(self, *prefixes: str, settings: Mapping[str, Any]):
        self.prefixes = prefixes
        self.settings = _dig_not_strict(settings, *prefixes)

    def _get_name(self, *fields: str) -> list[str]:
        return [field.replace("_", "-") for field in fields]

    def has_item(self, *fields: str) -> TOMLSource | None:
        names = self._get_name(*fields)
        try:
            _dig_strict(self.settings, *names)
            return self
        except KeyError:
            return None

    def get_item(self, *fields: str) -> Any:
        names = self._get_name(*fields)
        try:
            return _dig_strict(self.settings, *names)
        except KeyError:
            raise KeyError(f"{names!r} not found in configuration settings") from None

    @classmethod
    def convert(cls, item: Any, target: object) -> object:
        if isinstance(target, TypeLike) and hasattr(target, "__origin__"):
            if target.__origin__ == list:
                return [cls.convert(it, target.__args__[0]) for it in item]
            if target.__origin__ == Union:
                return cls.convert(item, _process_union(target))
        if callable(target):
            return target(item)
        raise AssertionError(f"Can't convert target {target}")

    def unrecognized_options(self, options: object) -> Generator[str, None, None]:
        yield from _unrecognized_dict(self.settings, options, self.prefixes)


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
            if field.default_factory is not dataclasses.MISSING:
                prep[field.name] = field.default_factory()
                continue

            errors.append(ValueError(f"Missing value for {field.name!r}"))

        if errors:
            prefix_str = ".".join(prefixes)
            raise ExceptionGroup(f"Failed converting {prefix_str}", errors)

        return target(**prep)

    def unrecognized_options(self, options: object) -> Generator[str, None, None]:
        for source in self.sources:
            yield from source.unrecognized_options(options)
