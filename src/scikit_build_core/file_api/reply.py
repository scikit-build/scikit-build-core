__lazy_modules__ = {
    "argparse",
    "dataclasses",
    f"{(__spec__.parent or '').rsplit('.', 1)[0]}._compat.builtins",
    f"{(__spec__.parent or '').rsplit('.', 1)[0]}._compat.typing",
    f"{(__spec__.parent or '').rsplit('.', 1)[0]}.utils.typing",
    f"{__spec__.parent}.model.cache",
    f"{__spec__.parent}.model.cmakefiles",
    f"{__spec__.parent}.model.codemodel",
    f"{__spec__.parent}.model.index",
    f"{__spec__.parent}.model.toolchains",
    "json",
    "pathlib",
}

import argparse
import builtins
import dataclasses
import json
import sys
import typing
from pathlib import Path
from typing import Any, Callable, Dict, List, Type, TypeVar, Union  # noqa: TID251

from .._compat.builtins import ExceptionGroup
from .._compat.typing import get_args, get_origin
from ..utils.typing import (
    get_target_raw_type,
    is_union_type,
    process_union,
)
from .model.cache import Cache
from .model.cmakefiles import CMakeFiles
from .model.codemodel import CodeModel, Target
from .model.index import Index
from .model.toolchains import Toolchains

__all__ = ["load_reply_dir"]


def __dir__() -> List[str]:
    return __all__


T = TypeVar("T")

InputDict = Dict[str, Any]


class Converter:
    def __init__(self, base_dir: Path) -> None:
        self.base_dir = base_dir

    def load(self) -> Index:
        """
        Load the newest index.json file and return the Index object.
        """
        index_file = sorted(self.base_dir.glob("index-*"))[-1]
        with index_file.open(encoding="utf-8") as f:
            data = json.load(f)

        return self.make_class(data, Index)

    def _load_from_json(self, name: Path, target: Type[T]) -> T:
        with self.base_dir.joinpath(name).open(encoding="utf-8") as f:
            data = json.load(f)

        return self.make_class(data, target)

    def make_class(self, data: InputDict, target: Type[T]) -> T:
        """
        Convert a dict to a dataclass. Automatically load a few nested jsonFile classes.
        """
        if (
            target in {CodeModel, Target, Cache, CMakeFiles, Toolchains}
            and "jsonFile" in data
            and data["jsonFile"] is not None
        ):
            return self._load_from_json(Path(data["jsonFile"]), target)

        input_dict: Dict[str, Type[Any]] = {}
        exceptions: List[Exception] = []

        # We don't have DataclassInstance exposed in typing yet
        for field in dataclasses.fields(target):  # type: ignore[arg-type]
            # A trailing underscore escapes a reserved word, like "from_"
            json_field = (
                field.name.rstrip("_")
                .replace("_v", "-v")
                .replace("cmakefiles", "cmakeFiles")
            )
            if json_field in data:
                field_type = field.type
                try:
                    input_dict[field.name] = self._convert_any(
                        data[json_field], field_type
                    )
                except TypeError as err:
                    msg = f"Failed to convert field {field.name!r} of type {field_type}"
                    if sys.version_info < (3, 11):
                        err.__notes__ = [*getattr(err, "__notes__", []), msg]  # type: ignore[attr-defined]
                    else:
                        err.add_note(msg)  # pylint: disable=no-member
                    exceptions.append(err)
                except ExceptionGroup as err:
                    exceptions.append(err)

        if exceptions:
            msg = f"Failed converting {target}"
            raise ExceptionGroup(msg, exceptions)

        return target(**input_dict)

    @typing.overload
    def _convert_any(self, item: Any, target: Type[T]) -> T: ...
    @typing.overload
    def _convert_any(self, item: Any, target: Any) -> Any: ...

    def _convert_any(self, item: Any, target: Union[Type[T], Any]) -> Any:
        target = process_union(target)
        if dataclasses.is_dataclass(target) and isinstance(target, type):
            # We don't have DataclassInstance exposed in typing yet
            return self.make_class(item, target)
        raw_target = get_target_raw_type(target)
        # For generic Unions we try each type one at a time. We first match the
        # shape of the item against the candidate, so that e.g. ``str(<dict>)``
        # cannot shadow a dataclass member in ``Union[str, Paths]``: a dict-like
        # item must go to a dataclass member, and any other item to a
        # non-dataclass member.
        if is_union_type(raw_target):
            last_err: Exception = TypeError(f"No member of {target} matched {item!r}")
            for maybe_target in get_args(target):
                sub_target = process_union(maybe_target)
                is_dataclass = dataclasses.is_dataclass(sub_target) and isinstance(
                    sub_target, type
                )
                if isinstance(item, dict) != is_dataclass:
                    continue
                try:
                    return self._convert_any(item, maybe_target)
                except (ExceptionGroup, TypeError) as err:
                    last_err = err
                    continue
            raise last_err

        origin = get_origin(target)
        if origin is list:
            return [self._convert_any(i, get_args(target)[0]) for i in item]

        return target(item)


def load_reply_dir(path: Path) -> Index:
    return Converter(path).load()


def main_reply(args: argparse.Namespace, /) -> None:
    rich_print: Callable[[object], None]
    try:
        from rich import print as rich_print
    except ModuleNotFoundError:
        rich_print = builtins.print

    reply = Path(args.reply_dir)
    rich_print(load_reply_dir(reply))


def populate_parser(parser: argparse.ArgumentParser, /) -> None:
    """Add the ``reply`` argument to an existing parser."""
    parser.add_argument("reply_dir", type=Path, help="Path to the reply directory")
    parser.set_defaults(func=main_reply)


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="python -m scikit_build_core.file_api.reply",
        allow_abbrev=False,
        description="Read a query written out to a build directory.",
    )
    populate_parser(parser)
    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
