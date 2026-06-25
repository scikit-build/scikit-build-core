from __future__ import annotations

import dataclasses
import importlib
import importlib.abc
import importlib.machinery
import inspect
import sys
from collections.abc import Iterator, Mapping
from pathlib import Path
from typing import TYPE_CHECKING, Any, Protocol, Union, runtime_checkable

if TYPE_CHECKING:
    from collections.abc import Generator, Sequence
    from importlib.machinery import ModuleSpec
    from types import ModuleType

    StrMapping = Mapping[str, Any]
else:
    StrMapping = Mapping

from ..metadata import _ALL_FIELDS

__all__ = ["load_provider", "process_dynamic_metadata"]


def __dir__() -> list[str]:
    return __all__


@runtime_checkable
class DynamicMetadataProtocol(Protocol):
    def dynamic_metadata(
        self,
        field: str,
        settings: dict[str, Any],
        project: Mapping[str, Any],
    ) -> Any: ...


@runtime_checkable
class DynamicMetadataRequirementsProtocol(DynamicMetadataProtocol, Protocol):
    def get_requires_for_dynamic_metadata(
        self, settings: dict[str, Any]
    ) -> list[str]: ...


@runtime_checkable
class DynamicMetadataWheelProtocol(DynamicMetadataProtocol, Protocol):
    def dynamic_wheel(self, field: str, settings: Mapping[str, Any]) -> bool: ...


DMProtocols = Union[
    DynamicMetadataProtocol,
    DynamicMetadataRequirementsProtocol,
    DynamicMetadataWheelProtocol,
]


class _ProviderPathFinder(importlib.abc.MetaPathFinder):
    """Load the top-level provider module from ``provider-path``.

    Mirrors how pyproject_hooks handles PEP 517 ``backend-path``: a finder at
    the front of ``sys.meta_path`` guarantees the in-tree provider wins over a
    same-named module elsewhere on ``sys.path`` (or behind another finder), and
    a provider absent from ``provider-path`` raises instead of silently
    importing the wrong module. Only the top-level name is intercepted; nested
    modules resolve through the parent package's path. A provider already cached
    in ``sys.modules`` short-circuits import and bypasses this finder.
    """

    def __init__(self, provider_path: list[str], provider: str) -> None:
        self.provider_path = provider_path
        self.provider = provider
        self.provider_parent = provider.partition(".")[0]

    def find_spec(
        self,
        fullname: str,
        _path: Sequence[str] | None,
        _target: ModuleType | None = None,
    ) -> ModuleSpec | None:
        if "." in fullname:
            return None

        spec = importlib.machinery.PathFinder.find_spec(
            fullname, path=self.provider_path
        )
        if spec is None and fullname == self.provider_parent:
            msg = f"Cannot find module {self.provider!r} in {self.provider_path!r}"
            raise ModuleNotFoundError(msg)
        return spec


def load_provider(
    provider: str,
    provider_path: str | None = None,
) -> DMProtocols:
    if provider_path is None:
        return importlib.import_module(provider)

    if not Path(provider_path).is_dir():
        msg = "provider-path must be an existing directory"
        raise AssertionError(msg)

    finder = _ProviderPathFinder([provider_path], provider)
    sys.meta_path.insert(0, finder)
    try:
        return importlib.import_module(provider)
    finally:
        sys.meta_path.remove(finder)


def _load_dynamic_metadata(
    metadata: Mapping[str, Mapping[str, str]],
) -> Generator[tuple[str, DMProtocols, dict[str, Any]], None, None]:
    for field, orig_config in metadata.items():
        if "provider" not in orig_config:
            msg = "Missing provider in dynamic metadata"
            raise KeyError(msg)

        if field not in _ALL_FIELDS:
            msg = f"{field} is not a valid field"
            raise KeyError(msg)
        config = dict(orig_config)
        provider = config.pop("provider")
        provider_path = config.pop("provider-path", None)
        loaded_provider = load_provider(provider, provider_path)
        yield field, loaded_provider, config


@dataclasses.dataclass
class DynamicPyProject(StrMapping):
    settings: dict[str, dict[str, Any]]
    project: dict[str, Any]
    providers: dict[str, DMProtocols]

    def __getitem__(self, key: str) -> Any:
        # Try to get the settings from either the static file or dynamic metadata provider
        if key in self.project:
            return self.project[key]

        # Check if we are in a loop, i.e. something else is already requesting
        # this key while trying to get another key
        if key not in self.providers:
            dep_type = "missing" if key in self.settings else "circular"
            msg = f"Encountered a {dep_type} dependency at {key}"
            raise ValueError(msg)

        provider = self.providers.pop(key)
        sig = inspect.signature(provider.dynamic_metadata)
        if len(sig.parameters) < 3:
            # Backcompat for dynamic_metadata without metadata dict
            self.project[key] = provider.dynamic_metadata(  # type: ignore[call-arg]
                key, self.settings[key]
            )
        else:
            self.project[key] = provider.dynamic_metadata(key, self.settings[key], self)
        self.project["dynamic"].remove(key)

        return self.project[key]

    def __iter__(self) -> Iterator[str]:
        # Iterate over the keys of the static settings
        yield from self.project

        # Iterate over the keys of the dynamic metadata providers
        # GraalPy needs it to be a copy
        yield from list(self.providers)

    def __len__(self) -> int:
        return len(self.project) + len(self.providers)

    def __contains__(self, key: object) -> bool:
        return key in self.project or key in self.providers


def process_dynamic_metadata(
    project: Mapping[str, Any],
    metadata: Mapping[str, Mapping[str, Any]],
) -> dict[str, Any]:
    initial = {f: (p, c) for (f, p, c) in _load_dynamic_metadata(metadata)}

    settings = DynamicPyProject(
        settings={f: c for f, (_, c) in initial.items()},
        project=dict(project),
        providers={k: v for k, (v, _) in initial.items()},
    )

    return dict(settings)
