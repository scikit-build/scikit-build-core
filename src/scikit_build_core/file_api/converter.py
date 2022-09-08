import json
from pathlib import Path
from typing import Any, Dict, Type, TypeVar

import cattr
import cattr.preconf.json

from .model.codemodel import CodeModel, Target
from .model.index import Index, Reply

T = TypeVar("T")

__all__ = ["make_converter", "read_index"]


def to_path(path: str, _: Type[Path]) -> Path:
    return Path(path)


def make_converter(base_dir: Path) -> cattr.preconf.json.JsonConverter:
    converter = cattr.preconf.json.make_converter()
    converter.register_structure_hook(Path, to_path)

    st_hook = cattr.gen.make_dict_structure_fn(
        Reply, converter, codemodel_v2=cattr.gen.override(rename="codemodel-v2")
    )
    converter.register_structure_hook(Reply, st_hook)

    def from_json_file(with_path: Dict[str, Any], t: Type[T]) -> T:
        path = base_dir / Path(with_path["jsonFile"])
        raw = json.loads(path.read_text(encoding="utf-8"))
        return converter.structure_attrs_fromdict(raw, t)

    converter.register_structure_hook(CodeModel, from_json_file)
    converter.register_structure_hook(Target, from_json_file)
    return converter


def read_index(reply_dir: Path) -> Index:
    converter = make_converter(reply_dir)
    indexes = sorted(reply_dir.glob("index-*"))
    if not indexes:
        raise IndexError(f"index file not found in {reply_dir}")
    index_file = indexes[0]
    return converter.loads(index_file.read_text(), Index)


if __name__ == "__main__":
    import rich

    reply = Path("tests/api/simple_pure/.cmake/api/v1/reply")
    rich.print(read_index(reply))
