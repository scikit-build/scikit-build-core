import dataclasses
import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Type, TypeVar

import cattr
import cattr.preconf.json

T = TypeVar("T")


@dataclasses.dataclass
class Version:
    major: int
    minor: int
    patch: int
    suffix: str
    string: str
    isDirty: bool


@dataclasses.dataclass
class Paths:
    cmake: Path
    ctest: Path
    cpack: Path
    root: Path


@dataclasses.dataclass
class Generator:
    multiConfig: bool
    name: str


@dataclasses.dataclass
class CMake:
    version: Version
    paths: Paths
    generator: Generator


@dataclasses.dataclass
class PathsSB:
    source: Path
    build: Path


@dataclasses.dataclass
class Directory:
    source: Path
    build: Path
    projectIndex: int
    hasInstallRule: Optional[bool] = None


@dataclasses.dataclass
class Project:
    name: str
    directoryIndexes: List[int]


@dataclasses.dataclass
class Artifact:
    path: Path


@dataclasses.dataclass
class Prefix:
    path: Path


@dataclasses.dataclass
class Destination:
    path: Path
    backtrace: Optional[int] = None


@dataclasses.dataclass
class Install:
    prefix: Prefix
    destinations: List[Destination]


@dataclasses.dataclass
class CommandFragment:
    fragment: str
    role: str


@dataclasses.dataclass
class Sysroot:
    path: Path


@dataclasses.dataclass
class Link:
    language: str
    commandFragments: List[CommandFragment]
    lto: Optional[bool] = None
    sysroot: Optional[Sysroot] = None


@dataclasses.dataclass
class Archive:
    commandFragments: List[CommandFragment] = dataclasses.field(default_factory=list)
    lto: Optional[bool] = None


@dataclasses.dataclass
class Dependency:
    id: str
    backtrace: Optional[int] = None


@dataclasses.dataclass
class Source:
    path: Path
    compileGroupIndex: Optional[int] = None
    sourceGroupIndex: Optional[int] = None
    isGenerated: Optional[bool] = None
    backtrace: Optional[int] = None


@dataclasses.dataclass
class Target:
    name: str
    id: str
    type: str
    paths: PathsSB
    sources = List[Source]
    nameOnDisk: Optional[Path] = None
    artifacts: List[Artifact] = dataclasses.field(default_factory=list)
    isGeneratorProvided: Optional[bool] = None
    install: Optional[Install] = None
    link: Optional[Link] = None
    archive: Optional[Archive] = None
    dependencies: List[Dependency] = dataclasses.field(default_factory=list)


@dataclasses.dataclass
class Configuration:
    name: str
    directories: List[Directory]
    projects: List[Project]
    targets: List[Target]


@dataclasses.dataclass
class CodeModel:
    paths: PathsSB
    configurations: List[Configuration]


@dataclasses.dataclass
class Reply:
    codemodel_v2: Optional[CodeModel]


@dataclasses.dataclass
class Index:
    cmake: CMake
    reply: Reply


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


def get_index(reply_dir: Path) -> Index:
    converter = make_converter(reply_dir)
    indexes = sorted(reply_dir.glob("index-*"))
    if not indexes:
        raise IndexError(f"index file not found in {reply_dir}")
    index_file = indexes[0]
    return converter.loads(index_file.read_text(), Index)


if __name__ == "__main__":
    import rich

    reply = Path("tests/api/simple_pure/.cmake/api/v1/reply")
    rich.print(get_index(reply))
