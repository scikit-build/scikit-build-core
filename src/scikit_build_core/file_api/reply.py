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
from .model._common import ObjectKind
from .model.cache import Cache
from .model.cmakefiles import CMakeFiles
from .model.codemodel import CodeModel, Target
from .model.directory import Directory
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
        # TODO: remove this special handling once everything is registered in `ObjectKind`
        if (
            target in {CodeModel, Target, Cache, CMakeFiles, Directory, Toolchains}
            and "jsonFile" in data
            and data["jsonFile"] is not None
        ):
            return self._load_from_json(Path(data["jsonFile"]), target)

        input_dict: Dict[str, Type[Any]] = {}
        exceptions: List[Exception] = []

        # We don't have DataclassInstance exposed in typing yet
        for field in dataclasses.fields(target):  # type: ignore[arg-type]
            json_field = field.name.replace("_v", "-v")
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

    def _convert_object_kind(self, data: Any) -> Any:
        """
        Special handling for ``ObjectKind`` types:
          * this gets the data from the file defined in ``jsonFile`` field instead
          * the actual type to use is defined in the ``kind``, ``version``
        """
        assert isinstance(data, dict)
        index_kind = data.pop("kind")
        index_version = data.pop("version")
        json_file = data.pop("jsonFile")
        with self.base_dir.joinpath(json_file).open(encoding="utf-8") as f:
            actual_data = json.load(f)
        kind = actual_data.pop("kind")
        version = actual_data.pop("version")
        if not (kind == index_kind and version == index_version):
            msg = f"Indexed object kind ({index_kind},{index_version}) does not match actual one ({kind},{version}) from {json_file}"
            raise ValueError(msg)
        # TODO: refine the type annotations
        target = ObjectKind.get_object_kind(kind=index_kind, version=index_version)
        return self.make_class(actual_data, target)

    @typing.overload
    def _convert_any(self, item: Any, target: Type[T]) -> T: ...
    @typing.overload
    def _convert_any(self, item: Any, target: Any) -> Any: ...

    def _convert_any(self, item: Any, target: Union[Type[T], Any]) -> Any:
        target = process_union(target)
        if isinstance(target, type) and issubclass(target, ObjectKind):
            # Special handling for ObjectKind, see inner comment
            return self._convert_object_kind(item)
        if dataclasses.is_dataclass(target) and isinstance(target, type):
            # We don't have DataclassInstance exposed in typing yet
            return self.make_class(item, target)
        raw_target = get_target_raw_type(target)
        # For generic Unions we try each type on at a time
        if is_union_type(raw_target):
            if all(
                isinstance(t, type) and issubclass(t, ObjectKind)
                for t in get_args(target)
            ):
                # Special handling for ObjectKind, see inner comment
                return self._convert_object_kind(item)
            last_err: Exception = AssertionError("Failed for unknown reason")
            for maybe_target in get_args(target):
                try:
                    return self._convert_any(item, maybe_target)
                except ExceptionGroup as err:  # noqa: PERF203
                    last_err = err
                    continue
            raise last_err

        origin = get_origin(target)
        if origin is not None and origin is list:
            return [self._convert_any(i, get_args(target)[0]) for i in item]

        return target(item)


def load_reply_dir(path: Path) -> Index:
    return Converter(path).load()


if __name__ == "__main__":
    import argparse

    rich_print: Callable[[object], None]
    try:
        from rich import print as rich_print
    except ModuleNotFoundError:
        rich_print = builtins.print

    parser = argparse.ArgumentParser(
        prog="python -m scikit_build_core.file_api.reply",
        allow_abbrev=False,
        description="Read a query written out to a build directory.",
    )
    parser.add_argument("reply_dir", type=Path, help="Path to the reply directory")
    args = parser.parse_args()

    reply = Path(args.reply_dir)
    rich_print(load_reply_dir(reply))
