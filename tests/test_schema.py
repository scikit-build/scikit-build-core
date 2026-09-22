from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from scikit_build_core._compat import tomllib
from scikit_build_core.settings.skbuild_schema import (
    generate_skbuild_schema,
    get_skbuild_schema,
)

DIR = Path(__file__).parent.resolve()

pytestmark = pytest.mark.upstream


def test_compare_schemas():
    """
    Should be the same. If not, run nox -s generate_schema
    """

    assert generate_skbuild_schema() == get_skbuild_schema()


SCHEMAS = [
    *DIR.parent.joinpath("docs/examples").glob("**/pyproject.toml"),
    *DIR.joinpath("packages").glob("**/pyproject.toml"),
]


@pytest.mark.parametrize(
    "filepath", SCHEMAS, ids=lambda x: str(x.relative_to(DIR.parent).parent)
)
def test_valid_schemas_files(filepath: Path) -> None:
    api = pytest.importorskip("validate_pyproject.api")

    with filepath.open("rb") as f:
        example = tomllib.load(f)

    validator = api.Validator()
    assert validator(example) is not None


@pytest.mark.parametrize(
    "addition",
    [
        {"minimum-version": 0.3},
        {"random": "not valid"},
        {"logging": {"level": "POODLE"}},
        {"generate": [{"path": "CMakeLists.txt"}]},
        {"generate": [{"path": "me.py", "template": "hi", "template-path": "hello"}]},
        {"generate": [{"path": "me.py", "template": ""}]},
        {"overrides": [{"cmake": {"args": ["-DFOO=BAR"]}}]},
        {"overrides": [{"select": {"python-version": ">=3.10"}}]},
        {
            "overrides": [
                {
                    "if": {"python-version": ">=3.10"},
                    "cmake.nonexist": ["-DFOO=BAR"],
                }
            ]
        },
        {"metadata": {"version": {"provider-path": True}}},
        {"metadata": {"version": {"provider": 2}}},
        {"metadata": {"invalid": {"provider": "correct"}}},
        {"cmake": {"define": {"FOO": {"env": ""}}}},
        {"cmake": {"define": {"FOO": {"default": False}}}},
        {"env": {"FOO": {"unknown": "x"}}},
        {"env": {"FOO": {"force": "not-a-bool"}}},
        {"config-setting": {"nodot": {"help": "x"}}},
        {"config-setting": {"zmq.prefix": {"unknown": "x"}}},
        {"config-setting": {"zmq.prefix": {"type": "int"}}},
        {"config-setting": {"zmq.prefix": {"env": ""}}},
        {"config-setting": {"zmq.prefix": {"choices": ["bundled"]}}},
        {"config-setting": {"zmq.prefix": {"cmake": "ZMQ_PREFIX"}}},
        {"cmake": {"define": {"FOO": {"config-setting": ""}}}},
        {
            "cmake": {
                "define": {"FOO": {"config-setting": "zmq.prefix", "default": "x"}}
            }
        },
        {
            "overrides": [
                {"if": {"config-setting": {}}, "cmake": {"args": ["-DFOO=BAR"]}}
            ]
        },
    ],
)
def test_invalid_schemas(addition: dict[str, Any]) -> None:
    fastjsonschema = pytest.importorskip("fastjsonschema")
    api = pytest.importorskip("validate_pyproject.api")

    example_toml = """\
    [project]
    name = "myproj"
    version = "0"

    [tool.scikit-build]
    minimum-version = "0.3"
    """

    example = tomllib.loads(example_toml)
    example["tool"]["scikit-build"].update(**addition)

    validator = api.Validator()
    print(example)
    with pytest.raises(fastjsonschema.JsonSchemaValueException):
        validator(example)


@pytest.mark.parametrize(
    "addition",
    [
        {"generate": [{"path": "CMakeLists.txt", "template": "hi"}]},
        {"generate": [{"path": "me.py", "template-path": "hello"}]},
        {
            "overrides": [
                {
                    "if": {"python-version": ">=3.10"},
                    "cmake": {"args": ["-DFOO=BAR"]},
                }
            ]
        },
        {"metadata": {"version": {"provider-path": "string"}}},
        {"metadata": {"description": {"anything": True}}},
        {"cmake": {"define": {"FOO": "BAR"}}},
        {"cmake": {"define": {"FOO": {"env": "FOO"}}}},
        {"cmake": {"define": {"FOO": {"env": "FOO", "default": False}}}},
        {"env": {"FOO": "bar"}},
        {"env": {"CMAKE_BUILD_PARALLEL_LEVEL": {"env": "MAX_JOBS"}}},
        {"env": {"FOO": {"env": "BAR", "default": "baz"}}},
        {"env": {"FOO": {"default": "bar", "force": True}}},
        {
            "config-setting": {
                "zmq.prefix": {"help": "Location", "env": "ZMQ_PREFIX"},
                "zmq.libzmq": {"help": "Where libzmq comes from", "default": "system"},
                "zmq.bundled": {"type": "bool", "default": False},
            }
        },
        {"cmake": {"define": {"FOO": {"config-setting": "zmq.prefix"}}}},
        {
            "overrides": [
                {
                    "if": {"config-setting": {"zmq.libzmq": "bundled"}},
                    "cmake": {"define": {"ZMQ_LIBZMQ": "ON"}},
                }
            ]
        },
    ],
)
def test_valid_schemas(addition: dict[str, Any]) -> None:
    api = pytest.importorskip("validate_pyproject.api")

    example_toml = """\
    [project]
    name = "myproj"
    version = "0"

    [tool.scikit-build]
    minimum-version = "0.3"
    """

    example = tomllib.loads(example_toml)
    example["tool"]["scikit-build"].update(**addition)

    validator = api.Validator()
    validator(example)


def test_required_names_normalized() -> None:
    """Required field names must be dash-normalized like the prop keys when
    normalize_keys is set, otherwise the schema would be unsatisfiable."""
    from schema_models import HasUnderscoreRequired

    from scikit_build_core.settings.json_schema import to_json_schema

    schema = to_json_schema(HasUnderscoreRequired, normalize_keys=True)
    assert schema["required"] == ["required-field"]
    assert set(schema["required"]) <= set(schema["properties"])

    schema = to_json_schema(HasUnderscoreRequired, normalize_keys=False)
    assert schema["required"] == ["required_field"]
    assert set(schema["required"]) <= set(schema["properties"])
