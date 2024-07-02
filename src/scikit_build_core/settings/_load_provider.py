from __future__ import annotations

import importlib
import sys
from pathlib import Path
from typing import TYPE_CHECKING, Any, Protocol, Union

if TYPE_CHECKING:
    from collections.abc import Generator, Iterable, Mapping

__all__ = ["load_dynamic_metadata", "load_provider"]


def __dir__() -> list[str]:
    return __all__


class DynamicMetadataProtocol(Protocol):
    def dynamic_metadata(
        self, fields: Iterable[str], settings: dict[str, Any]
    ) -> dict[str, Any]: ...


class DynamicMetadataRequirementsProtocol(DynamicMetadataProtocol, Protocol):
    def get_requires_for_dynamic_metadata(
        self, settings: dict[str, Any]
    ) -> list[str]: ...


class DynamicMetadataWheelProtocol(DynamicMetadataProtocol, Protocol):
    def dynamic_wheel(
        self, field: str, settings: Mapping[str, Any] | None = None
    ) -> bool: ...


class DynamicMetadataRequirementsWheelProtocol(
    DynamicMetadataRequirementsProtocol, DynamicMetadataWheelProtocol, Protocol
): ...


DMProtocols = Union[
    DynamicMetadataProtocol,
    DynamicMetadataRequirementsProtocol,
    DynamicMetadataWheelProtocol,
    DynamicMetadataRequirementsWheelProtocol,
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


def load_dynamic_metadata(
    metadata: Mapping[str, Mapping[str, str]],
) -> Generator[tuple[str, DMProtocols | None, dict[str, str]], None, None]:
    for field, orig_config in metadata.items():
        if "provider" in orig_config:
            config = dict(orig_config)
            provider = config.pop("provider")
            provider_path = config.pop("provider-path", None)
            yield field, load_provider(provider, provider_path), config
        else:
            yield field, None, dict(orig_config)
