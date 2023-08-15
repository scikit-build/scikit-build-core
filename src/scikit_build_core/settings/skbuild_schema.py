from __future__ import annotations

import copy
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

    schema = {
        "$schema": "http://json-schema.org/draft-07/schema",
        "$id": "https://github.com/scikit-build/scikit-build-core/blob/main/src/scikit_build_core/resources/scikit-build.schema.json",
        "description": "Scikit-build-core's settings.",
        **to_json_schema(ScikitBuildSettings, normalize_keys=True),
    }

    # Manipulate a bit to get better validation
    # This is making the generate's template or template-path required
    generate = schema["properties"]["generate"]["items"]
    for prop in generate["properties"].values():
        if prop.get("type", "") == "string":
            prop["minLength"] = 1
    generate_tmpl = copy.deepcopy(generate)
    generate_path = copy.deepcopy(generate)

    generate_tmpl["required"] = ["path", "template"]
    del generate_tmpl["properties"]["template-path"]
    del generate_tmpl["properties"]["template"]["default"]

    generate_path["required"] = ["path", "template-path"]
    del generate_path["properties"]["template"]

    schema["properties"]["generate"]["items"] = {
        "oneOf": [generate_tmpl, generate_path]
    }

    return schema


def get_skbuild_schema(tool_name: str = "scikit-build") -> dict[str, Any]:
    "Get the stored complete schema for scikit-build settings."
    assert tool_name == "scikit-build", "Only scikit-build is supported."

    with resources.joinpath("scikit-build.schema.json").open(encoding="utf-8") as f:
        return json.load(f)  # type: ignore[no-any-return]


if __name__ == "__main__":
    d = generate_skbuild_schema()
    print(json.dumps(d, indent=2))  # noqa: T201
