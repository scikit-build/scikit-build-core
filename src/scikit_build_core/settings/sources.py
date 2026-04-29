"""
This module implements the configuration sources used by scikit-build-core.
Each concrete :class:`Source` adapts one input representation, such as
environment variables, PEP 517 ``config-settings``, or nested TOML tables, into
the same nested dataclass model. :class:`SourceChain` combines those sources and
applies them in precedence order when building the final settings object.

An end user usually interacts with :class:`SourceChain`, which takes a
dataclass type and returns an instance with fields populated.

Example of usage::

    sources = SourceChain(TOMLSource("tool", "mypackage", settings=pyproject_dict), ...)
    settings = sources.convert_target(SomeSettingsModel)

    unrecognized_options = list(sources.unrecognized_options(SomeSettingsModel))


Naming conventions:

- ``model`` is the complete Dataclass.
- ``target`` is the type to convert a single item to.
- ``settings`` is the input data source (unless it already has a name, like
  ``env``).
- ``options`` are the names of the items in the ``model``, formatted in the
  style of the current Source.
- ``fields`` are the tuple of strings describing a nested field in the
  ``model``.

Source representations:

- :class:`EnvSource`: stores values in environment variables. Lists are encoded
  as ``"a;b"`` and dicts as ``"key=value;other=value"``.
- :class:`ConfSource`: stores values in a flat mapping keyed by dotted option
  names.
- :class:`TOMLSource`: stores values in a nested TOML mapping.
- :class:`SourceChain`: queries sources in order and asks the first matching
  source to convert its native value into the requested dataclass field type.

When setting up your dataclasses, these types are handled:

- ``str``: A string type, nothing special.
- ``bool``: Supports bool in TOML, not handled in envvar/config (so only useful in a Union)
- Any callable (`Path`, `Version`): Passed the string input.
- ``Optional[T]``: Treated like T. Default should be None, since no input format supports None's.
- ``Union[str, ...]``: Supports other input types in TOML form (bool currently). Otherwise a string.
- ``List[T]``: A list of items. `;` separated supported in EnvVar/config forms. T can be a dataclass (TOML only).
- ``Dict[str, T]``: A table of items. TOML supports a layer of nesting. Any is supported as an item type.
- ``Union[list[T], Dict[str, T]]`` (TOML only): A list or dict of items.
- ``Literal[...]``: A list of strings, the result must be in the list.
- ``Annotated[Dict[...], "EnvVar"]``: A dict of items, where each item can be a string or a dict with "env" and "default" keys.

These are supported for JSON schema generation for the TOML, as well.

Integers/floats would be easy to add, but haven't been needed yet.
"""

from __future__ import annotations

import dataclasses
import os
import typing
from typing import Any, Literal, Protocol, TypeVar

from .._compat.builtins import ExceptionGroup
from .._compat.typing import get_args
from ..utils.typing import (
    get_inner_type,
    get_target_raw_type,
    is_union_type,
    process_annotated,
    process_union,
)

if typing.TYPE_CHECKING:
    from collections.abc import Generator, Iterator, Mapping, Sequence


T = TypeVar("T")

__all__ = ["ConfSource", "EnvSource", "Source", "SourceChain", "TOMLSource"]


def __dir__() -> list[str]:
    return __all__


def _dig_strict(_dict: Mapping[str, Any], /, *names: str) -> Any:
    """
    Walk a nested mapping and return the value at ``names``.

    Each input ``name`` is one nesting level.

    :raises KeyError: when ``names`` is missing
    """
    for name in names:
        _dict = _dict[name]
    return _dict


def _process_bool(value: str) -> bool:
    return value.strip().lower() not in {"0", "false", "off", "no", ""}


def _dig_not_strict(_dict: Mapping[str, Any], /, *names: str) -> Any:
    """
    Walk a nested mapping like :func:`_dig_strict`, but return an empty dict
    ``{}`` if any name in ``names`` is missing.
    """
    for name in names:
        _dict = _dict.get(name, {})
    return _dict


def _dig_fields(opt: Any, /, *names: str) -> Any:
    """
    Walk dataclass field annotations and return the annotation at ``names``.

    ``opt`` is a dataclass type, and each entry in ``names`` is a nested field
    name to follow.
    """
    for name in names:
        fields = dataclasses.fields(opt)
        types = [x.type for x in fields if x.name == name]
        if len(types) != 1:
            msg = f"Could not access {'.'.join(names)}"
            raise KeyError(msg)
        (opt,) = types
    return opt


def _nested_dataclass_to_names(
    target: type[Any] | Any, /, *inner: str
) -> Iterator[list[str]]:
    """
    Yield field-name paths for every leaf in a nested dataclass model.

    For example, a nested field ``a.b.c`` is yielded as ``["a", "b", "c"]``.
    """

    if dataclasses.is_dataclass(target) and isinstance(target, type):
        for field in dataclasses.fields(target):
            yield from _nested_dataclass_to_names(field.type, *inner, field.name)
    else:
        yield list(inner)


def _dict_with_envvar(target: Any, /) -> Any:
    """
    Resolve ``{"env": ..., "default": ...}`` dict entries into a final value.

    The input is either a literal value or a small config dict used by the
    ``Annotated[..., "EnvVar"]`` TOML form. The return value is the resolved
    envvar/default value, with bool defaults preserving bool conversion.
    """
    if not isinstance(target, dict):
        return target
    env = target["env"]
    default = target.get("default", None)
    value = os.environ.get(env, default)
    if isinstance(default, bool) and isinstance(value, str):
        return _process_bool(value)
    return value


class Source(Protocol):
    def has_item(self, *fields: str, is_dict: bool) -> bool:
        """
        Check whether the source contains a field path.

        For example, ``fields=("a", "b")`` asks whether the source has a value
        for the nested model field ``a.b``. ``is_dict`` is set for dict-typed
        targets, because some sources represent dict entries as nested keys.
        """
        ...

    def get_item(self, *fields: str, is_dict: bool) -> Any:
        """
        Return the source-native value for a field path.

        The return type depends on the source: env returns a raw string,
        config-settings returns a string/list/bool or reconstructed dict, and
        TOML returns the native TOML object. Raises ``KeyError`` if the value is
        missing. ``is_dict`` is set for dict-typed targets, because some
        sources represent dict entries as nested keys.
        """
        ...

    @classmethod
    def convert(cls, item: Any, target: type[Any] | Any) -> object:
        """
        Convert a source-native ``item`` into the requested ``target`` type.

        Raises ``TypeError`` if the conversion fails.
        """
        ...

    def unrecognized_options(self, options: object) -> Generator[str, None, None]:
        """
        Given a model, produce an iterator of all unrecognized option names.
        Empty iterator if this can't be computed for the source (like for
        environment variables).
        """
        ...

    def all_option_names(self, target: type[Any]) -> Iterator[str]:
        """
        Given a model, produce a list of all possible names (used for producing
        suggestions).
        """
        ...


class EnvSource(Source):
    """
    Source backed by environment variables.

    Nested field paths are represented by uppercased underscore-separated names
    such as ``PREFIX_A_B``. Values remain raw strings in the environment until
    they are converted into the requested field type.
    """

    def __init__(self, prefix: str, *, env: Mapping[str, str] | None = None) -> None:
        self.env = env or os.environ
        self.prefix = prefix

    def _get_name(self, *fields: str) -> str:
        names = [field.upper() for field in fields]
        return "_".join([self.prefix, *names] if self.prefix else names)

    def has_item(self, *fields: str, is_dict: bool) -> bool:  # noqa: ARG002
        name = self._get_name(*fields)
        return bool(self.env.get(name, ""))

    def get_item(
        self,
        *fields: str,
        is_dict: bool,  # noqa: ARG002
    ) -> str | dict[str, str]:
        name = self._get_name(*fields)
        if name in self.env:
            return self.env[name]
        msg = f"{name!r} not found in environment"
        raise KeyError(msg)

    @classmethod
    def convert(cls, item: str, target: type[Any] | Any) -> object:
        """
        Convert an item from the environment (always a string) into a target type.
        """
        target, _ = process_annotated(target)
        raw_target = get_target_raw_type(target)
        if dataclasses.is_dataclass(raw_target):
            msg = f"Array of dataclasses are not supported in configuration settings ({raw_target})"
            raise TypeError(msg)
        if raw_target is list:
            return [
                cls.convert(i.strip(), get_inner_type(target)) for i in item.split(";")
            ]
        if raw_target is dict:
            items = (i.strip().split("=") for i in item.split(";"))
            return {k: cls.convert(v, get_inner_type(target)) for k, v in items}

        if raw_target is bool:
            return _process_bool(item)

        if is_union_type(raw_target) and str in get_args(target):
            return item

        if is_union_type(raw_target):
            args = {get_target_raw_type(t): t for t in get_args(target)}
            if str in args:
                return item
            if dict in args and "=" in item:
                items = (i.strip().split("=") for i in item.split(";"))
                return {k: cls.convert(v, get_inner_type(args[dict])) for k, v in items}
            if list in args:
                return [
                    cls.convert(i.strip(), get_inner_type(args[list]))
                    for i in item.split(";")
                ]
            msg = f"Can't convert into {target}"
            raise TypeError(msg)

        if raw_target is Literal:
            if item not in get_args(process_union(target)):
                msg = f"{item!r} not in {get_args(process_union(target))!r}"
                raise TypeError(msg)
            return item

        if callable(raw_target):
            return raw_target(item)
        msg = f"Can't convert target {target}"
        raise TypeError(msg)

    @staticmethod
    def unrecognized_options(  # pylint: disable=arguments-differ
        options: object,  # noqa: ARG004
    ) -> Generator[str, None, None]:
        yield from ()

    def all_option_names(self, target: type[Any]) -> Iterator[str]:
        prefix = [self.prefix] if self.prefix else []
        for names in _nested_dataclass_to_names(target):
            yield "_".join(prefix + names).upper()


def _unrecognized_dict(
    settings: Mapping[str, Any], options: Any, above: Sequence[str]
) -> Generator[str, None, None]:
    """
    Compare a nested TOML-style mapping against a dataclass model.

    ``settings`` is the current nested dict to inspect, ``options`` is the
    dataclass type for that level, and ``above`` is the already-traversed key
    path used when yielding fully qualified option names.
    """
    for keystr in settings:
        # We don't have DataclassInstance exposed in typing yet
        matches = [
            x for x in dataclasses.fields(options) if x.name.replace("_", "-") == keystr
        ]
        if not matches:
            yield ".".join((*above, keystr))
            continue
        (inner_option_field,) = matches
        inner_option = inner_option_field.type
        if dataclasses.is_dataclass(inner_option) and isinstance(inner_option, type):
            yield from _unrecognized_dict(
                settings[keystr], inner_option, (*above, keystr)
            )


class ConfSource(Source):
    """
    Source for PEP 517 ``config-settings``.

    While most mechanisms (pip, uv, build) only support text, gpep517 allows an
    arbitrary json input, so this currently also handles bools.
    """

    prefixes: tuple[str, ...]
    """Dotted option-name segments prepended to every lookup."""

    settings: Mapping[str, str | list[str] | bool]
    """
    Flat backend ``config-settings`` mapping keyed by dotted option names.

    Scalar values are stored directly. Dict-typed target fields are represented
    by multiple flat entries such as ``"sdist.include.foo" = "bar"``.
    """

    verify: bool
    """
    Whether to report unrecognized dotted keys from this source.

    Only disable this when the source intentionally shares a namespace with
    unrelated config keys.
    """

    def __init__(
        self,
        *prefixes: str,
        settings: Mapping[str, str | list[str] | bool],
        verify: bool = True,
    ) -> None:
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

    def get_item(
        self, *fields: str, is_dict: bool
    ) -> str | list[str] | dict[str, str] | bool:
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
            msg = f"Dict items {name}.* not found in settings"
            raise KeyError(msg)
        if name in self.settings:
            return self.settings[name]

        msg = f"{name!r} not found in configuration settings"
        raise KeyError(msg)

    @classmethod
    def convert(
        cls, item: str | list[str] | dict[str, str] | bool, target: type[Any] | Any
    ) -> object:
        target, _ = process_annotated(target)
        raw_target = get_target_raw_type(target)
        if dataclasses.is_dataclass(raw_target):
            msg = f"Array of dataclasses are not supported in configuration settings ({raw_target})"
            raise TypeError(msg)
        if raw_target is list:
            if isinstance(item, list):
                return [cls.convert(i, get_inner_type(target)) for i in item]
            if isinstance(item, (dict, bool)):
                msg = f"Expected {target}, got {type(item)}"
                raise TypeError(msg)
            return [
                cls.convert(i.strip(), get_inner_type(target)) for i in item.split(";")
            ]
        if raw_target is dict:
            assert not isinstance(item, (str, list, bool))
            return {k: cls.convert(v, get_inner_type(target)) for k, v in item.items()}
        if is_union_type(raw_target):
            args = {get_target_raw_type(t): t for t in get_args(target)}
            if str in args:
                return item
            if dict in args and isinstance(item, dict):
                return {
                    k: cls.convert(v, get_inner_type(args[dict]))
                    for k, v in item.items()
                }
            if list in args and isinstance(item, list):
                return [cls.convert(i, get_inner_type(args[list])) for i in item]
            msg = f"Can't convert into {target}"
            raise TypeError(msg)
        if isinstance(item, (list, dict)):
            msg = f"Expected {target}, got {type(item).__name__}"
            raise TypeError(msg)
        if raw_target is bool:
            return item if isinstance(item, bool) else _process_bool(item)
        if raw_target is Literal:
            if item not in get_args(process_union(target)):
                msg = f"{item!r} not in {get_args(process_union(target))!r}"
                raise TypeError(msg)
            return item
        if callable(raw_target):
            return raw_target(item)
        msg = f"Can't convert target {target}"
        raise TypeError(msg)

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
            if get_target_raw_type(outer_option) is dict:
                continue

    def all_option_names(self, target: type[Any]) -> Iterator[str]:
        for names in _nested_dataclass_to_names(target):
            dash_names = [name.replace("_", "-") for name in names]
            yield ".".join((*self.prefixes, *dash_names))


class TOMLSource(Source):
    """
    Source backed by a nested TOML mapping.

    After applying any constructor prefixes, ``self.settings`` is the nested
    table for that subtree. ``get_item`` returns the native TOML value found at
    the requested field path, and ``convert`` turns that TOML value into the
    target dataclass field type.
    """

    def __init__(self, *prefixes: str, settings: Mapping[str, Any]) -> None:
        self.prefixes = prefixes
        self.settings = _dig_not_strict(settings, *prefixes)

    @staticmethod
    def _get_name(*fields: str) -> list[str]:
        return [field.replace("_", "-") for field in fields]

    def has_item(self, *fields: str, is_dict: bool) -> bool:  # noqa: ARG002
        names = self._get_name(*fields)
        try:
            _dig_strict(self.settings, *names)
        except KeyError:
            return False
        return True

    def get_item(self, *fields: str, is_dict: bool) -> Any:  # noqa: ARG002
        names = self._get_name(*fields)
        try:
            return _dig_strict(self.settings, *names)
        except KeyError:
            msg = f"{names!r} not found in configuration settings"
            raise KeyError(msg) from None

    @classmethod
    def convert(cls, item: Any, target: type[Any] | Any) -> object:
        """
        Convert an ``item`` from TOML into a ``target`` type.
        """
        target, annotations = process_annotated(target)
        raw_target = get_target_raw_type(target)
        if dataclasses.is_dataclass(raw_target) and isinstance(raw_target, type):
            fields = dataclasses.fields(raw_target)
            values = ((k.replace("-", "_"), v) for k, v in item.items())
            return raw_target(
                **{
                    k: cls.convert(v, *[f.type for f in fields if f.name == k])
                    for k, v in values
                }
            )
        if raw_target is list:
            if not isinstance(item, list):
                msg = f"Expected {target}, got {type(item).__name__}"
                raise TypeError(msg)
            return [cls.convert(it, get_inner_type(target)) for it in item]
        if raw_target is dict:
            if not isinstance(item, dict):
                msg = f"Expected {target}, got {type(item).__name__}"
                raise TypeError(msg)
            if annotations == ("EnvVar",):
                return {
                    k: cls.convert(_dict_with_envvar(v), get_inner_type(target))
                    for k, v in item.items()
                    if _dict_with_envvar(v) is not None
                }
            return {k: cls.convert(v, get_inner_type(target)) for k, v in item.items()}
        if raw_target is Any:
            return item
        if is_union_type(raw_target):
            args = {get_target_raw_type(t): t for t in get_args(target)}
            if type(item) in args:
                if isinstance(item, dict):
                    return {
                        k: cls.convert(v, get_inner_type(args[dict]))
                        for k, v in item.items()
                    }
                if isinstance(item, list):
                    return [cls.convert(i, get_inner_type(args[list])) for i in item]
                return item
        if raw_target is Literal:
            if item not in get_args(process_union(target)):
                msg = f"{item!r} not in {get_args(process_union(target))!r}"
                raise TypeError(msg)
            return item
        if callable(raw_target):
            return raw_target(item)
        msg = f"Can't convert target {target}"
        raise TypeError(msg)

    def unrecognized_options(self, options: object) -> Generator[str, None, None]:
        yield from _unrecognized_dict(self.settings, options, self.prefixes)

    def all_option_names(self, target: type[Any]) -> Iterator[str]:
        for names in _nested_dataclass_to_names(target):
            dash_names = [name.replace("_", "-") for name in names]
            yield ".".join((*self.prefixes, *dash_names))


class SourceChain:
    def __init__(self, *sources: Source, prefixes: Sequence[str] = ()) -> None:
        """
        Combine a collection of sources into a single object that can run
        ``convert_target(dataclass)``.  An optional list of prefixes can be
        given that will be prepended (dot separated) to error messages.
        """
        self.sources = sources
        self.prefixes = prefixes

    def __getitem__(self, index: int) -> Source:
        return self.sources[index]

    def has_item(self, *fields: str, is_dict: bool) -> bool:
        return any(source.has_item(*fields, is_dict=is_dict) for source in self.sources)

    def get_item(self, *fields: str, is_dict: bool) -> Any:
        for source in self.sources:
            if source.has_item(*fields, is_dict=is_dict):
                return source.get_item(*fields, is_dict=is_dict)
        msg = f"{fields!r} not found in any source"
        raise KeyError(msg)

    def convert_target(self, target: type[T], *prefixes: str) -> T:
        """
        Build a dataclass instance from the chained sources.

        For each field, this first asks each source whether it has a native
        value for the current path. The first matching source returns that raw
        value via ``get_item``, and that same source then normalizes it with
        ``convert`` into the dataclass field type. Nested dataclasses recurse
        into ``convert_target``. Dict fields are special: later sources extend
        the dict assembled so far instead of replacing it outright.
        """

        errors = []
        prep: dict[str, Any] = {}
        for field in dataclasses.fields(target):  # type: ignore[arg-type]
            if dataclasses.is_dataclass(field.type) and isinstance(field.type, type):
                try:
                    prep[field.name] = self.convert_target(
                        field.type, *prefixes, field.name
                    )
                except Exception as e:  # noqa: BLE001
                    name = ".".join([*self.prefixes, *prefixes, field.name])
                    e.__notes__ = [*getattr(e, "__notes__", []), f"Field: {name}"]  # type: ignore[attr-defined]
                    errors.append(e)
                continue

            is_dict = get_target_raw_type(field.type) is dict

            for source in self.sources:
                if source.has_item(*prefixes, field.name, is_dict=is_dict):
                    simple = source.get_item(*prefixes, field.name, is_dict=is_dict)
                    try:
                        tmp = source.convert(simple, field.type)
                    except Exception as e:  # noqa: BLE001
                        name = ".".join([*self.prefixes, *prefixes, field.name])
                        e.__notes__ = [*getattr(e, "__notes__", []), f"Field {name}"]  # type: ignore[attr-defined]
                        errors.append(e)
                        prep[field.name] = None
                        break

                    if is_dict:
                        # Dict sources merge by precedence: later matching sources
                        # add missing keys without erasing higher-priority ones.
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
            prefix_str = ".".join([*self.prefixes, *prefixes])
            msg = f"Failed converting {prefix_str}"
            raise ExceptionGroup(msg, errors)

        return target(**prep)

    def unrecognized_options(self, options: object) -> Generator[str, None, None]:
        for source in self.sources:
            yield from source.unrecognized_options(options)
