from typing import Any

import pytest

from scikit_build_core.builder._load_provider import process_dynamic_metadata
from scikit_build_core.metadata import _process_dynamic_metadata


def test_template_basic() -> None:
    pyproject = process_dynamic_metadata(
        {
            "name": "test",
            "version": "0.1.0",
            "dynamic": ["requires-python"],
        },
        {
            "requires-python": {
                "provider": "scikit_build_core.metadata.template",
                "result": ">={project[version]}",
            },
        },
    )

    assert pyproject["requires-python"] == ">=0.1.0"


def test_template_needs() -> None:
    # These are intentionally out of order to test the order of processing
    pyproject = process_dynamic_metadata(
        {
            "name": "test",
            "version": "0.1.0",
            "dynamic": ["requires-python", "license", "readme"],
        },
        {
            "license": {
                "provider": "scikit_build_core.metadata.template",
                "result": "{project[requires-python]}",
            },
            "readme": {
                "provider": "scikit_build_core.metadata.template",
                "result": {"file": "{project[license]}"},
            },
            "requires-python": {
                "provider": "scikit_build_core.metadata.template",
                "result": ">={project[version]}",
            },
        },
    )

    assert pyproject["requires-python"] == ">=0.1.0"


def test_regex() -> None:
    pyproject = process_dynamic_metadata(
        {
            "name": "test",
            "version": "0.1.0",
            "dynamic": ["requires-python"],
        },
        {
            "requires-python": {
                "provider": "scikit_build_core.metadata.regex",
                "input": "pyproject.toml",
                "regex": r"name = \"(?P<name>.+)\"",
                "result": ">={name}",
            },
        },
    )

    assert pyproject["requires-python"] == ">=scikit_build_core"


@pytest.mark.parametrize(
    ("field", "input_", "output"),
    [
        pytest.param("version", "{sub}", "42", id="str"),
        pytest.param("classifiers", ["a", "{sub}"], ["a", "42"], id="list-str"),
        pytest.param(
            "scripts",
            {"a": "{sub}", "{sub}": "b"},
            {"a": "42", "42": "b"},
            id="dict-str",
        ),
        pytest.param(
            "authors", [{"name": "{sub}"}], [{"name": "42"}], id="list-dict-str"
        ),
        pytest.param(
            "optional-dependencies",
            {"dev": ["{sub}"]},
            {"dev": ["42"]},
            id="dict-list-str",
        ),
        pytest.param("readme", {"text": "{sub}"}, {"text": "42"}, id="readme"),
        pytest.param(
            "entry-points",
            {"ep": {"{sub}": "{sub}"}},
            {"ep": {"42": "42"}},
            id="dict-dict-str",
        ),
    ],
)
def test_actions(field: str, input_: Any, output: Any) -> None:
    result = _process_dynamic_metadata(field, lambda x: x.format(sub=42), input_)
    assert output == result


@pytest.mark.parametrize(
    ("field", "bad_input", "match"),
    [
        pytest.param(
            "version",
            ["not", "a", "string"],
            "must be a string",
            id="str-field-not-str",
        ),
        pytest.param(
            "classifiers",
            "not-a-list",
            "must be a list of strings",
            id="list-str-field-not-list",
        ),
        pytest.param(
            "scripts",
            "not-a-dict",
            "must be a dictionary of strings",
            id="dict-str-field-not-dict",
        ),
        pytest.param(
            "authors",
            "not-a-list",
            "must be a dictionary of strings",
            id="list-dict-field-not-list",
        ),
        pytest.param(
            "entry-points",
            "not-a-dict",
            "must be a dictionary of dictionary of strings",
            id="entry-points-not-dict",
        ),
        pytest.param(
            "optional-dependencies",
            "not-a-dict",
            "must be a dictionary of lists",
            id="optional-deps-not-dict",
        ),
    ],
)
def test_actions_type_errors(field: str, bad_input: Any, match: str) -> None:
    with pytest.raises(RuntimeError, match=match):
        _process_dynamic_metadata(field, lambda x: x, bad_input)


def test_actions_unsupported_field() -> None:
    with pytest.raises(RuntimeError, match="Unsupported field"):
        _process_dynamic_metadata("not-a-real-field", lambda x: x, "anything")
