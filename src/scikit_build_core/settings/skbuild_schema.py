from __future__ import annotations

import json
from typing import Any

from ..resources import resources

__all__ = ["get_skbuild_schema", "generate_skbuild_schema"]


def __dir__() -> list[str]:
    return __all__


def generate_skbuild_schema(tool_name: str = "scikit-build") -> dict[str, Any]:
    "Generate the complete schema for scikit-build settings."
    assert tool_name == "scikit-build", "Only scikit-build is supported."

    from .json_schema import to_json_schema
    from .skbuild_model import ScikitBuildSettings

    return {
        "$schema": "http://json-schema.org/draft-07/schema",
        "$id": "https://github.com/scikit-build/scikit-build-core/blob/main/src/scikit_build_core/resources/scikit-build.schema.json",
        "description": "Scikit-build-core's settings.",
        **to_json_schema(ScikitBuildSettings, normalize_keys=True),
    }


def get_skbuild_schema(tool_name: str = "scikit-build") -> dict[str, Any]:
    "Get the stored complete schema for scikit-build settings."
    assert tool_name == "scikit-build", "Only scikit-build is supported."

    with resources.joinpath("scikit-build.schema.json").open(encoding="utf-8") as f:
        return json.load(f)  # type: ignore[no-any-return]


if __name__ == "__main__":
    d = generate_skbuild_schema()
    print(json.dumps(d, indent=2))  # noqa: T201
