import dataclasses
from abc import ABC
from functools import total_ordering
from pathlib import Path
from typing import ClassVar, List, Union

from ..._logging import logger

__all__ = ["APIVersion", "ObjectKind", "Paths"]


def __dir__() -> List[str]:
    return __all__


@total_ordering
@dataclasses.dataclass(frozen=True, eq=True)
class APIVersion:
    major: int
    minor: int

    def __gt__(self, other: "APIVersion") -> bool:
        if not isinstance(other, APIVersion):
            raise NotImplementedError
        if self.major > other.major:
            return True
        if self.major < other.major:
            return False
        if self.minor > other.minor:
            return True
        if self.minor < other.minor:
            return False
        return False

    def __str__(self) -> str:
        return f"{self.major}.{self.minor}"


@dataclasses.dataclass(frozen=True)
class Paths:
    source: Path
    build: Path


class ObjectKind(ABC):
    kind: ClassVar[str]
    version: ClassVar[APIVersion]
    _objectkind_registrar: ClassVar[dict[str, set[type["ObjectKind"]]]] = {}

    def __init_subclass__(cls) -> None:
        registrar = cls._objectkind_registrar.setdefault(cls.kind, set())
        registrar.add(cls)

    @classmethod
    def get_object_kind(
        cls, kind: str, version: Union[APIVersion, dict[str, int]]
    ) -> type["ObjectKind"]:
        if isinstance(version, dict):
            return cls.get_object_kind(
                kind=kind,
                version=APIVersion(major=version["major"], minor=version["minor"]),
            )
        registrar = cls._objectkind_registrar[kind]
        for object_kind in registrar:
            if version == object_kind.version:
                return object_kind
        assert version > object_kind.version
        logger.warning(
            "The file-api object kind '{} {}' has not been registered in scikit-build-core",
            kind,
            version,
        )
        logger.debug("Using best guess {}", object_kind.__name__)
        return object_kind


class ObjectKindSubType:
    _registrar: ClassVar[set[type["ObjectKindSubType"]]] = set()

    def __init_subclass__(cls) -> None:
        cls._registrar.add(cls)
