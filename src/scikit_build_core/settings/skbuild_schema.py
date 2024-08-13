from __future__ import annotations

import copy
import json
from typing import Any

from ..resources import resources

__all__ = ["generate_skbuild_schema", "get_skbuild_schema"]


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
    schema["$defs"]["if_overrides"] = {
        "type": "object",
        "minProperties": 1,
        "additionalProperties": False,
        "properties": {
            "scikit-build-version": {
                "type": "string",
                "description": "The version of scikit-build-version. Takes a specifier set.",
            },
            "python-version": {
                "type": "string",
                "description": "The two-digit Python version. Takes a specifier set.",
            },
            "implementation-name": {
                "type": "string",
                "description": "The value of `sys.implementation.name`. Takes a regex",
            },
            "implementation-version": {
                "type": "string",
                "description": "Derived from `sys.implementation.version`, following PEP 508. Takes a specifier set.",
            },
            "platform-system": {
                "type": "string",
                "description": "The value of `sys.platform`. Takes a regex.",
            },
            "platform-machine": {
                "type": "string",
                "description": "The value of `platform.machine()`. Takes a regex.",
            },
            "platform-node": {
                "type": "string",
                "description": "The value of `platform.node()`. Takes a regex.",
            },
            "state": {
                "type": "string",
                "description": "The state of the build, one of `sdist`, `wheel`, `editable`, `metadata_wheel`, and `metadata_editable`. Takes a regex.",
            },
            "from-sdist": {
                "type": "boolean",
                "description": "Whether the build is from an sdist.",
            },
            "failed": {
                "type": "boolean",
                "description": "Matches if the build fails. A build will be retried if there is at least one matching override with this set to true.",
            },
            "system-cmake": {
                "type": "string",
                "description": "The version of CMake found on the system. Takes a specifier set.",
            },
            "cmake-wheel": {
                "type": "boolean",
                "description": "Whether a cmake wheel is known to be provided for this system.",
            },
            "abi-flags": {
                "type": "string",
                "description": "A sorted string of the abi flags. Takes a regex.",
            },
            "env": {
                "type": "object",
                "patternProperties": {
                    ".*": {"oneOf": [{"type": "string"}, {"type": "boolean"}]}
                },
                "additionalProperties": False,
                "minProperties": 1,
                "description": "A table of environment variables mapped to either string regexs, or booleans. Valid 'truthy' environment variables are case insensitive `true`, `on`, `yes`, `y`, `t`, or a number more than 0.",
            },
        },
    }
    schema["$defs"]["inherit"] = {
        "enum": ["none", "append", "prepend"],
        "default": "none",
    }

    inherit_props: dict[str, Any] = {
        k: {
            kk: {"$ref": "#/$defs/inherit"}
            for kk, vv in v["properties"].items()
            if vv.get("type", "") in {"object", "array"}
            or any(
                vvv.get("type", "") in {"object", "array"}
                for vvv in vv.get("oneOf", {})
            )
        }
        for k, v in schema["properties"].items()
        if v.get("type", "") == "object"
    }
    inherit_props = {
        k: {"type": "object", "additionalProperties": False, "properties": v}
        for k, v in inherit_props.items()
        if v
    }

    schema["properties"]["overrides"] = {
        "type": "array",
        "description": "A list of overrides to apply to the settings, based on the `if` selector.",
        "items": {
            "type": "object",
            "required": ["if"],
            "minProperties": 2,
            "additionalProperties": False,
            "properties": {
                "if": {
                    "anyOf": [
                        {"$ref": "#/$defs/if_overrides"},
                        {
                            "type": "object",
                            "properties": {"any": {"$ref": "#/$defs/if_overrides"}},
                            "required": ["any"],
                            "additionalProperties": False,
                        },
                    ]
                },
                "inherit": {
                    "type": "object",
                    "properties": inherit_props,
                    "additionalProperties": False,
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
