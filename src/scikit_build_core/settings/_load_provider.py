from __future__ import annotations

import importlib
import sys
from collections.abc import Iterable
from pathlib import Path
from typing import Any

from .._compat.typing import Protocol

__all__ = ["load_provider"]


def __dir__() -> list[str]:
    return __all__


class DynamicMetadataProtocol(Protocol):
    def dynamic_metadata(
        self, fields: Iterable[str], settings: dict[str, Any]
    ) -> dict[str, Any]:
        ...


class DynamicMetadataRequirementsProtocol(DynamicMetadataProtocol, Protocol):
    def get_requires_for_dynamic_metadata(self, settings: dict[str, Any]) -> list[str]:
        ...


def load_provider(
    provider: str,
    provider_path: str | None = None,
) -> DynamicMetadataProtocol | DynamicMetadataRequirementsProtocol:
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
