from __future__ import annotations

__all__ = ["dynamic_metadata"]


def __dir__() -> list[str]:
    return __all__


def dynamic_metadata(
    fields: frozenset[str],
    settings: dict[str, object] | None = None,
) -> dict[str, str | dict[str, str | None]]:
    if fields != {"version"}:
        msg = "Only the 'version' field is supported"
        raise ValueError(msg)

    if settings:
        msg = "No inline configuration is supported"
        raise ValueError(msg)

    return {"version": "3.2.1"}
