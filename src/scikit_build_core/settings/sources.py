from __future__ import annotations

import dataclasses
import os
from collections.abc import Generator, Iterator, Mapping, Sequence
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


def _dig_fields(__opt: object, *names: str) -> Any:
    for name in names:
        fields = dataclasses.fields(__opt)
        types = [x.type for x in fields if x.name == name]
        if len(types) != 1:
            raise KeyError("Could not access {'.'.join(names)}")
        (__opt,) = types
    return __opt


@runtime_checkable
class TypeLike(Protocol):
    @property
    def __origin__(self) -> Any:
        ...

    @property
    def __args__(self) -> list[Any]:
        ...


def _process_union(target: type[Any]) -> Any:
    """
    Selects the non-None item in an Optional or Optional-like Union. Passes through non-Unions.
    """

    if (
        not isinstance(target, TypeLike)
        or not hasattr(target, "__origin__")
        or target.__origin__ is not Union
    ):
        return target

    if len(target.__args__) == 2:
        items = list(target.__args__)
        if type(None) not in items:
            raise AssertionError(f"None must be in union, got {items}")
        items.remove(type(None))
        return items[0]

    raise AssertionError("Only Unions with None supported")


def _get_target_raw_type(target: type[Any]) -> type[Any]:
    """
    Takes a type like Optional[str] and returns str,
    or Optional[Dict[str, int]] and returns dict.
    """

    target = _process_union(target)
    # The hasattr is required for Python 3.7, though not quite sure why
    if isinstance(target, TypeLike) and hasattr(target, "__origin__"):
        return target.__origin__
    return target


def _get_inner_type(target: type[Any]) -> type[Any]:
    """
    Takes a types like List[str] and returns str,
    or Dict[str, int] and returns int.
    """

    raw_target = _get_target_raw_type(target)
    target = _process_union(target)
    if raw_target == list:
        assert isinstance(target, TypeLike)
        return target.__args__[0]
    if raw_target == dict:
        assert isinstance(target, TypeLike)
        return target.__args__[1]
    raise AssertionError("Expected a list or dict")


def _nested_dataclass_to_names(target: type[Any], *inner: str) -> Iterator[list[str]]:
    """
    Yields each entry, like ("a", "b", "c") for a.b.c
    """

    if dataclasses.is_dataclass(target):
        for field in dataclasses.fields(target):
            yield from _nested_dataclass_to_names(field.type, *inner, field.name)
    else:
        yield list(inner)


class Source(Protocol):
    def has_item(self, *fields: str, is_dict: bool) -> bool:
        """
        Check if the source contains a chain of fields. For example, feilds =
        [Field(name="a"), Field(name="b")] will check if the source contains the
        key "a.b".
        """
        ...

    def get_item(self, *fields: str, is_dict: bool) -> Any:
        ...

    @classmethod
    def convert(cls, item: Any, target: type[Any]) -> object:
        ...

    def unrecognized_options(self, options: object) -> Generator[str, None, None]:
        ...

    def all_option_names(self, target: type[Any]) -> Iterator[str]:
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

    # pylint: disable-next=unused-argument
    def has_item(self, *fields: str, is_dict: bool) -> bool:
        name = self._get_name(*fields)
        return name in self.env and self.env[name] != ""

    # pylint: disable-next=unused-argument
    def get_item(self, *fields: str, is_dict: bool) -> str | dict[str, str]:
        name = self._get_name(*fields)
        if name in self.env:
            return self.env[name]
        raise KeyError(f"{name!r} not found in environment")

    @classmethod
    def convert(cls, item: str, target: type[Any]) -> object:
        raw_target = _get_target_raw_type(target)
        if raw_target == list:
            return [
                cls.convert(i.strip(), _get_inner_type(target)) for i in item.split(";")
            ]
        if raw_target == dict:
            items = (i.strip().split("=") for i in item.split(";"))
            return {k: cls.convert(v, _get_inner_type(target)) for k, v in items}

        if raw_target is bool:
            result = item.strip().lower() not in {"0", "false", "off", "no", ""}
            return result

        if callable(raw_target):
            return raw_target(item)
        raise AssertionError(f"Can't convert target {target}")

    # pylint: disable-next=unused-argument
    def unrecognized_options(self, options: object) -> Generator[str, None, None]:
        yield from ()

    def all_option_names(self, target: type[Any]) -> Iterator[str]:
        prefix = [self.prefix] if self.prefix else []
        for names in _nested_dataclass_to_names(target):
            yield "_".join(prefix + names).upper()


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

    def has_item(self, *fields: str, is_dict: bool) -> bool:
        names = self._get_name(*fields)
        name = ".".join(names)

        if is_dict:
            return any(k.startswith(f"{name}.") for k in self.settings)

        return name in self.settings

    def get_item(self, *fields: str, is_dict: bool) -> str | list[str] | dict[str, str]:
        names = self._get_name(*fields)
        name = ".".join(names)
        if is_dict:
            d = {
                k[len(name) + 1 :]: str(v)
                for k, v in self.settings.items()
                if k.startswith(f"{name}.")
            }
            if d:
                return d
            raise KeyError(f"Dict items {name}.* not found in settings")
        if name in self.settings:
            return self.settings[name]

        raise KeyError(f"{name!r} not found in configuration settings")

    @classmethod
    def convert(
        cls, item: str | list[str] | dict[str, str], target: type[Any]
    ) -> object:
        raw_target = _get_target_raw_type(target)
        if raw_target == list:
            if isinstance(item, list):
                return [cls.convert(i, _get_inner_type(target)) for i in item]
            assert not isinstance(item, dict)
            return [
                cls.convert(i.strip(), _get_inner_type(target)) for i in item.split(";")
            ]
        if raw_target == dict:
            assert not isinstance(item, (str, list))
            return {k: cls.convert(v, _get_inner_type(target)) for k, v in item.items()}
        assert not isinstance(
            item, (list, dict)
        ), "Can't convert list or dict to non-list/dict"
        if raw_target is bool:
            result = item.strip().lower() not in {"0", "false", "off", "no", ""}
            return result
        if callable(raw_target):
            return raw_target(item)
        raise AssertionError(f"Can't convert target {target}")

    def unrecognized_options(self, options: object) -> Generator[str, None, None]:
        if not self.verify:
            return
        for keystr in self.settings:
            keys = keystr.replace("-", "_").split(".")[len(self.prefixes) :]
            try:
                outer_option = _dig_fields(options, *keys[:-1])
            except KeyError:
                yield ".".join(keystr.split(".")[:-1])
                continue
            if dataclasses.is_dataclass(outer_option):
                try:
                    _dig_fields(outer_option, keys[-1])
                except KeyError:
                    yield keystr
                    continue
            if _get_target_raw_type(outer_option) == dict:
                continue

    def all_option_names(self, target: type[Any]) -> Iterator[str]:
        for names in _nested_dataclass_to_names(target):
            dash_names = [name.replace("_", "-") for name in names]
            yield ".".join((*self.prefixes, *dash_names))


class TOMLSource:
    def __init__(self, *prefixes: str, settings: Mapping[str, Any]):
        self.prefixes = prefixes
        self.settings = _dig_not_strict(settings, *prefixes)

    def _get_name(self, *fields: str) -> list[str]:
        return [field.replace("_", "-") for field in fields]

    # pylint: disable-next=unused-argument
    def has_item(self, *fields: str, is_dict: bool) -> bool:
        names = self._get_name(*fields)
        try:
            _dig_strict(self.settings, *names)
            return True
        except KeyError:
            return False

    # pylint: disable-next=unused-argument
    def get_item(self, *fields: str, is_dict: bool) -> Any:
        names = self._get_name(*fields)
        try:
            return _dig_strict(self.settings, *names)
        except KeyError:
            raise KeyError(f"{names!r} not found in configuration settings") from None

    @classmethod
    def convert(cls, item: Any, target: type[Any]) -> object:
        raw_target = _get_target_raw_type(target)
        if raw_target == list:
            return [cls.convert(it, _get_inner_type(target)) for it in item]
        if raw_target == dict:
            return {k: cls.convert(v, _get_inner_type(target)) for k, v in item.items()}
        if callable(raw_target):
            return raw_target(item)
        raise AssertionError(f"Can't convert target {target}")

    def unrecognized_options(self, options: object) -> Generator[str, None, None]:
        yield from _unrecognized_dict(self.settings, options, self.prefixes)

    def all_option_names(self, target: type[Any]) -> Iterator[str]:
        for names in _nested_dataclass_to_names(target):
            dash_names = [name.replace("_", "-") for name in names]
            yield ".".join((*self.prefixes, *dash_names))


class SourceChain:
    def __init__(self, *sources: Source) -> None:
        self.sources = sources

    def __getitem__(self, index: int) -> Source:
        return self.sources[index]

    def has_item(self, *fields: str, is_dict: bool) -> bool:
        for source in self.sources:
            if source.has_item(*fields, is_dict=is_dict):
                return True
        return False

    def get_item(self, *fields: str, is_dict: bool) -> Any:
        for source in self.sources:
            if source.has_item(*fields, is_dict=is_dict):
                return source.get_item(*fields, is_dict=is_dict)
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

            is_dict = _get_target_raw_type(field.type) == dict

            for source in self.sources:
                if source.has_item(*prefixes, field.name, is_dict=is_dict):
                    simple = source.get_item(*prefixes, field.name, is_dict=is_dict)
                    try:
                        tmp = source.convert(simple, field.type)
                    except Exception as e:
                        errors.append(e)
                        prep[field.name] = None
                        break

                    if is_dict:
                        assert isinstance(tmp, dict), f"{field.name} must be a dict"
                        prep[field.name] = {**tmp, **prep.get(field.name, {})}
                        continue

                    prep[field.name] = tmp
                    break

            if field.name in prep:
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

    def all_option_names(self, target: type[Any]) -> Iterator[str]:
        for source in self.sources:
            yield from source.all_option_names(target)
