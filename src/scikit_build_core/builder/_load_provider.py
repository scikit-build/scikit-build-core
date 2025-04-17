from __future__ import annotations

import importlib
import sys
from pathlib import Path
from typing import TYPE_CHECKING, Any, Protocol, Union, runtime_checkable

from .._compat.graphlib import TopologicalSorter

if TYPE_CHECKING:
    from collections.abc import Generator, Iterable, Mapping

__all__ = ["load_dynamic_metadata", "load_provider"]


def __dir__() -> list[str]:
    return __all__


@runtime_checkable
class DynamicMetadataProtocol(Protocol):
    def dynamic_metadata(
        self, fields: Iterable[str], settings: dict[str, Any], metadata: dict[str, Any]
    ) -> dict[str, Any]: ...


@runtime_checkable
class DynamicMetadataRequirementsProtocol(DynamicMetadataProtocol, Protocol):
    def get_requires_for_dynamic_metadata(
        self, settings: dict[str, Any]
    ) -> list[str]: ...


@runtime_checkable
class DynamicMetadataWheelProtocol(DynamicMetadataProtocol, Protocol):
    def dynamic_wheel(
        self, field: str, settings: Mapping[str, Any] | None = None
    ) -> bool: ...


@runtime_checkable
class DynamicMetadataNeeds(DynamicMetadataProtocol, Protocol):
    def dynamic_metadata_needs(
        self,
        field: str,
        settings: Mapping[str, object] | None = None,
    ) -> list[str]: ...


DMProtocols = Union[
    DynamicMetadataProtocol,
    DynamicMetadataRequirementsProtocol,
    DynamicMetadataWheelProtocol,
    DynamicMetadataNeeds,
]


def load_provider(
    provider: str,
    provider_path: str | None = None,
) -> DMProtocols:
    if provider_path is None:
        return importlib.import_module(provider)

    if not Path(provider_path).is_dir():
        msg = "provider-path must be an existing directory"
        raise AssertionError(msg)

    try:
        sys.path.insert(0, provider_path)
        return importlib.import_module(provider)
    finally:
        sys.path.pop(0)


def _load_dynamic_metadata(
    metadata: Mapping[str, Mapping[str, str]],
) -> Generator[
    tuple[str, DMProtocols | None, dict[str, str], frozenset[str]], None, None
]:
    for field, orig_config in metadata.items():
        if "provider" in orig_config:
            config = dict(orig_config)
            provider = config.pop("provider")
            provider_path = config.pop("provider-path", None)
            loaded_provider = load_provider(provider, provider_path)
            needs = frozenset(
                loaded_provider.dynamic_metadata_needs(field, config)
                if isinstance(loaded_provider, DynamicMetadataNeeds)
                else []
            )
            yield field, loaded_provider, config, needs
        else:
            yield field, None, dict(orig_config), frozenset()


def load_dynamic_metadata(
    metadata: Mapping[str, Mapping[str, str]],
) -> list[tuple[str, DMProtocols | None, dict[str, str]]]:
    initial = {f: (p, c, n) for (f, p, c, n) in _load_dynamic_metadata(metadata)}
    sorter = TopologicalSorter({f: n for f, (_, _, n) in initial.items()})
    order = sorter.static_order()
    return [(f, *initial[f][:2]) for f in order]
