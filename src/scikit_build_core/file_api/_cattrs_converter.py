# pylint: disable=duplicate-code

import builtins
import json
from dataclasses import fields
from pathlib import Path
from typing import Any, Callable, Dict, Type, TypeVar  # noqa: TID251

import cattr
import cattr.preconf.json

from ..utils.typing import get_target_raw_type, is_union_type, process_union
from .model._common import ObjectKind
from .model.codemodel import Target
from .model.index import Index, Reply

T = TypeVar("T")

__all__ = ["load_reply_dir", "make_converter"]


def to_path(path: str, _: Type[Path]) -> Path:
    return Path(path)


def make_converter(base_dir: Path) -> cattr.preconf.json.JsonConverter:
    converter = cattr.preconf.json.make_converter()
    converter.register_structure_hook(Path, to_path)

    def from_json_file_old(with_path: Dict[str, Any], t: Type[T]) -> T:
        t = process_union(t)
        if with_path["jsonFile"] is None:
            return converter.structure_attrs_fromdict({}, t)
        path = base_dir / Path(with_path["jsonFile"])
        raw = json.loads(path.read_text(encoding="utf-8"))
        return converter.structure_attrs_fromdict(raw, t)

    def from_json_file(with_path: Dict[str, Any], t: Type[T]) -> T:
        index_kind = with_path.pop("kind")
        index_version = with_path.pop("version")
        if with_path["jsonFile"] is None:
            msg = f"Unexpected missing jsonFile [{type(t)}]: {with_path}"
            raise ValueError(msg)
        path = base_dir / Path(with_path["jsonFile"])
        raw = json.loads(path.read_text(encoding="utf-8"))
        kind = raw.pop("kind")
        version = raw.pop("version")
        # This cattrs flow is used only for testing, the asserts should be enough here
        assert index_kind == kind
        assert index_version == version
        target = ObjectKind.get_object_kind(kind=kind, version=version)
        # Note: mypy handling manually in the part above, hard to make it static
        return converter.structure_attrs_fromdict(raw, target)  # type: ignore[return-value]

    overrides = {}
    for f in fields(Reply):
        raw_type = get_target_raw_type(f.type)
        if is_union_type(raw_type):
            # TODO: this check should be no longer necessary at the end of the refactor
            # Handle multi-versioned objects
            type_override = cattr.gen.override(
                rename=f.name.replace("_", "-"),
                struct_hook=from_json_file,
            )
        else:
            # Previous default handling that does not read the kind and version
            type_override = cattr.gen.override(
                rename=f.name.replace("_", "-"),
                struct_hook=from_json_file_old,
            )
        overrides[f.name] = type_override

    converter.register_structure_hook(
        Reply,
        cattr.gen.make_dict_structure_fn(
            Reply,
            converter,
            # mypy fails over here for some reason, but this approach is as documented
            **overrides,  # type: ignore[arg-type]
        ),
    )
    # Other indirectly `jsonFile` loadable fields
    # TODO: Get this list of functions more programmatically
    for object_kind_type in (Target,):
        converter.register_structure_hook(object_kind_type, from_json_file_old)
    return converter


def load_reply_dir(reply_dir: Path) -> Index:
    converter = make_converter(reply_dir)
    indexes = sorted(reply_dir.glob("index-*"))
    if not indexes:
        msg = f"index file not found in {reply_dir}"
        raise IndexError(msg)
    index_file = indexes[-1]
    return converter.loads(index_file.read_text("utf-8"), Index)


if __name__ == "__main__":
    import argparse

    rich_print: Callable[[object], None]
    try:
        from rich import print as rich_print
    except ModuleNotFoundError:
        rich_print = builtins.print

    parser = argparse.ArgumentParser(
        allow_abbrev=False,
        description="This runs cattrs (required) instead of the built-in converter, for comparison.",
    )
    parser.add_argument("reply_dir", type=Path, help="Path to the reply directory")
    args = parser.parse_args()

    reply = Path(args.reply_dir)
    rich_print(load_reply_dir(reply))
