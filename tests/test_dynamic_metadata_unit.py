from pathlib import Path
from typing import Any

import pytest

from scikit_build_core.builder._load_provider import (
    load_provider,
    process_dynamic_metadata,
)
from scikit_build_core.metadata import _process_dynamic_metadata
from scikit_build_core.metadata.regex import dynamic_metadata as regex_dynamic_metadata
from scikit_build_core.metadata.template import (
    dynamic_metadata as template_dynamic_metadata,
)


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


def test_regex_rejects_bogus_key() -> None:
    # A typo'd key (here "removes") must raise, not be silently ignored.
    with pytest.raises(RuntimeError, match="settings allowed"):
        regex_dynamic_metadata(
            "version",
            {"input": "pyproject.toml", "removes": "x"},
        )


def test_template_rejects_bogus_key() -> None:
    with pytest.raises(RuntimeError, match="settings allowed"):
        template_dynamic_metadata(
            "version",
            {"result": "{project[version]}", "removes": "x"},
            {"version": "0.1.0"},
        )


def test_list_dict_field_rejects_non_dict() -> None:
    # ``authors``/``maintainers`` given a list of strings must raise a
    # RuntimeError (previously raised AttributeError from .items()).
    with pytest.raises(RuntimeError, match="list of dictionaries of strings"):
        _process_dynamic_metadata("authors", lambda x: x, ["not-a-dict"])


def test_optional_dependencies_rejects_non_str_elements() -> None:
    bad: Any = {"dev": [42]}
    with pytest.raises(RuntimeError, match="lists of strings"):
        _process_dynamic_metadata("optional-dependencies", lambda x: x, bad)


def test_load_provider_path_loads_local(tmp_path: Path) -> None:
    plugin_dir = tmp_path / "plugins"
    plugin_dir.mkdir()
    (plugin_dir / "local_prov_ok.py").write_text(
        "def dynamic_metadata(field, settings, project):\n    return '1.2.3'\n"
    )

    provider = load_provider("local_prov_ok", str(plugin_dir))
    version: Any = provider.dynamic_metadata("version", {}, {})
    assert version == "1.2.3"


def test_load_provider_path_not_shadowed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # A same-named module reachable via the normal sys.path ...
    other = tmp_path / "other"
    other.mkdir()
    (other / "shadow_prov.py").write_text("WRONG = True\n")
    monkeypatch.syspath_prepend(str(other))

    # ... must not satisfy a provider-path request that does not contain it.
    empty = tmp_path / "empty"
    empty.mkdir()
    with pytest.raises(ModuleNotFoundError):
        load_provider("shadow_prov", str(empty))
