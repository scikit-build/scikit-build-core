from __future__ import annotations

import copy
import json
from typing import Any

from ..resources import resources

__all__ = ["get_skbuild_schema", "generate_skbuild_schema"]


def __dir__() -> list[str]:
    return __all__


METADATA = [
    "version",
    "description",
    "license",
    "readme",
    "requires-python",
    "dependencies",
    "optional-dependencies",
    "entrypoints",
    "authors",
    "maintainers",
    "urls",
    "classifiers",
    "keywords",
    "scripts",
    "gui-scripts",
]


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

    schema["$defs"] = {
        "metadata": {
            "type": "object",
            "properties": {
                "provider": {"type": "string"},
                "provider-path": {"type": "string"},
            },
        }
    }

    del schema["properties"]["metadata"]["patternProperties"]
    schema["properties"]["metadata"]["additionalProperties"] = False
    schema["properties"]["metadata"]["properties"] = {
        m: {"$ref": "#/$defs/metadata"} for m in METADATA
    }

    props = {k: {"$ref": f"#/properties/{k}"} for k in schema["properties"]}
    schema["properties"]["overrides"] = {
        "type": "array",
        "items": {
            "type": "object",
            "required": ["if"],
            "minProperties": 2,
            "additionalProperties": False,
            "properties": {
                "if": {
                    "type": "object",
                    "minProperties": 1,
                    "additionalProperties": False,
                    "properties": {
                        "python-version": {"type": "string"},
                        "implementation-name": {"type": "string"},
                        "implementation-version": {"type": "string"},
                        "platform-system": {"type": "string"},
                        "platform-machine": {"type": "string"},
                        "platform-node": {"type": "string"},
                    },
                },
                **props,
            },
        },
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
