from pathlib import Path
from typing import Any

import pytest

from scikit_build_core._compat.importlib.metadata import entry_points
from scikit_build_core.builder._load_provider import (
    load_provider,
    process_dynamic_metadata,
    process_legacy_dynamic_metadata,
)
from scikit_build_core.metadata import _process_dynamic_metadata
from scikit_build_core.metadata.fancy_pypi_readme import Provider as FancyProvider
from scikit_build_core.metadata.regex import Provider as RegexProvider
from scikit_build_core.metadata.regex import dynamic_metadata as regex_dynamic_metadata
from scikit_build_core.metadata.setuptools_scm import Provider as ScmProvider
from scikit_build_core.metadata.template import Provider as TemplateProvider
from scikit_build_core.metadata.template import (
    dynamic_metadata as template_dynamic_metadata,
)


def test_template_basic() -> None:
    pyproject = process_legacy_dynamic_metadata(
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
    pyproject = process_legacy_dynamic_metadata(
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
    pyproject = process_legacy_dynamic_metadata(
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
    hook: Any = provider.dynamic_metadata
    assert hook("version", {}, {}) == "1.2.3"


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


def test_array_regex_via_field_setting() -> None:
    # The bundled regex plugin is reached by its entry-point name in the 0.3
    # array form; the new-style wrapper sources the target from ``field``.
    project = process_dynamic_metadata(
        {"name": "test", "version": "0.1.0", "dynamic": ["requires-python"]},
        [
            {
                "provider": "scikit_build_core.metadata.regex",
                "field": "requires-python",
                "input": "pyproject.toml",
                "regex": r"name = \"(?P<name>.+)\"",
                "result": ">={name}",
            }
        ],
    )
    assert project["requires-python"] == ">=scikit_build_core"
    assert "requires-python" not in project["dynamic"]


def test_array_runs_in_order() -> None:
    # A later entry reads a field an earlier entry produced.
    project = process_dynamic_metadata(
        {"name": "test", "version": "0.1.0", "dynamic": ["requires-python", "license"]},
        [
            {
                "provider": "scikit_build_core.metadata.template",
                "field": "requires-python",
                "result": ">={project[version]}",
            },
            {
                "provider": "scikit_build_core.metadata.template",
                "field": "license",
                "result": "needs {project[requires-python]}",
            },
        ],
    )
    assert project["requires-python"] == ">=0.1.0"
    assert project["license"] == "needs >=0.1.0"


def test_array_forward_reference_raises() -> None:
    # Unlike the legacy table, the array resolves strictly in order, so reading
    # a not-yet-produced field is a plain KeyError.
    with pytest.raises(KeyError):
        process_dynamic_metadata(
            {
                "name": "t",
                "version": "0.1.0",
                "dynamic": ["requires-python", "license"],
            },
            [
                {
                    "provider": "scikit_build_core.metadata.template",
                    "field": "requires-python",
                    "result": "{project[license]}",
                },
                {
                    "provider": "scikit_build_core.metadata.template",
                    "field": "license",
                    "result": "MIT",
                },
            ],
        )


def _write_provider(tmp_path: Path, name: str, body: str) -> str:
    plugin_dir = tmp_path / "plugins"
    plugin_dir.mkdir(exist_ok=True)
    (plugin_dir / f"{name}.py").write_text(body)
    return str(plugin_dir)


def test_array_new_style_multi_field(tmp_path: Path) -> None:
    path = _write_provider(
        tmp_path,
        "multi_prov",
        "def dynamic_metadata(settings, project):\n"
        "    return {'version': '1.2.3', 'description': 'hi'}\n",
    )
    project = process_dynamic_metadata(
        {"name": "t", "dynamic": ["version", "description"]},
        [{"provider": {"path": path, "module": "multi_prov"}}],
    )
    assert project["version"] == "1.2.3"
    assert project["description"] == "hi"
    assert project["dynamic"] == []


def test_array_pep808_add_only_list(tmp_path: Path) -> None:
    path = _write_provider(
        tmp_path,
        "deps_prov",
        "def dynamic_metadata(settings, project):\n"
        "    return {'dependencies': ['numpy']}\n",
    )
    project = process_dynamic_metadata(
        {"name": "t", "dependencies": ["torch"], "dynamic": ["dependencies"]},
        [{"provider": {"path": path, "module": "deps_prov"}}],
    )
    # Existing static entries kept first, provider additions appended.
    assert project["dependencies"] == ["torch", "numpy"]


def test_array_scalar_static_and_dynamic_raises(tmp_path: Path) -> None:
    path = _write_provider(
        tmp_path,
        "ver_prov",
        "def dynamic_metadata(settings, project):\n    return {'version': '9'}\n",
    )
    with pytest.raises(ValueError, match="both statically and dynamically"):
        process_dynamic_metadata(
            {"name": "t", "version": "1.0", "dynamic": ["version"]},
            [{"provider": {"path": path, "module": "ver_prov"}}],
        )


def test_array_field_not_in_dynamic_raises(tmp_path: Path) -> None:
    path = _write_provider(
        tmp_path,
        "ver_prov2",
        "def dynamic_metadata(settings, project):\n    return {'version': '9'}\n",
    )
    with pytest.raises(KeyError, match="must be listed in project"):
        process_dynamic_metadata(
            {"name": "t", "dynamic": []},
            [{"provider": {"path": path, "module": "ver_prov2"}}],
        )


def test_array_build_state_hook(tmp_path: Path) -> None:
    path = _write_provider(
        tmp_path,
        "state_prov",
        "class Provider:\n"
        "    def build_state(self, build_state):\n"
        "        self.state = build_state\n"
        "    def dynamic_metadata(self, settings, project):\n"
        "        return {'version': self.state}\n",
    )
    project = process_dynamic_metadata(
        {"name": "t", "dynamic": ["version"]},
        [{"provider": {"path": path, "module": "state_prov:Provider"}}],
        build_state="sdist",
    )
    assert project["version"] == "sdist"


def test_array_bad_build_state_raises() -> None:
    with pytest.raises(ValueError, match="build_state must be one of"):
        process_dynamic_metadata(
            {"name": "t", "dynamic": ["version"]},
            [],
            build_state="bogus",  # type: ignore[arg-type]
        )


def test_array_missing_provider_raises() -> None:
    with pytest.raises(KeyError, match="must set a 'provider'"):
        process_dynamic_metadata(
            {"name": "t", "dynamic": ["version"]},
            [{"field": "version"}],
        )


def test_regex_provider_new_style() -> None:
    # The new-style wrapper takes (settings, project) and reads the target from
    # the ``field`` setting, returning a {field: value} fragment.
    fragment = RegexProvider.dynamic_metadata(
        {
            "field": "requires-python",
            "input": "pyproject.toml",
            "regex": r"name = \"(?P<name>.+)\"",
            "result": ">={name}",
        },
        {},
    )
    assert fragment == {"requires-python": ">=scikit_build_core"}


def test_template_provider_new_style() -> None:
    fragment = TemplateProvider.dynamic_metadata(
        {"field": "requires-python", "result": ">={project[version]}"},
        {"version": "0.1.0"},
    )
    assert fragment == {"requires-python": ">=0.1.0"}


def test_provider_requires_field() -> None:
    with pytest.raises(RuntimeError, match="requires a 'field' setting"):
        RegexProvider.dynamic_metadata({"input": "pyproject.toml"}, {})


def test_scm_provider_defaults_field_and_requires() -> None:
    # setuptools_scm only ever sets version, so ``field`` defaults to "version".
    assert ScmProvider.get_requires_for_dynamic_metadata({}) == ["setuptools-scm"]


def test_fancy_provider_defaults_field_and_requires() -> None:
    assert FancyProvider.get_requires_for_dynamic_metadata({}) == [
        "hatch-fancy-pypi-readme>=23.2"
    ]


def test_bundled_providers_registered_as_entry_points() -> None:
    eps = {
        ep.name: ep.value
        for ep in entry_points(group="dynamic_metadata.provider")
        if ep.name.startswith("scikit_build_core.")
    }
    assert eps == {
        "scikit_build_core.metadata.regex": "scikit_build_core.metadata.regex:Provider",
        "scikit_build_core.metadata.template": "scikit_build_core.metadata.template:Provider",
        "scikit_build_core.metadata.setuptools_scm": "scikit_build_core.metadata.setuptools_scm:Provider",
        "scikit_build_core.metadata.fancy_pypi_readme": "scikit_build_core.metadata.fancy_pypi_readme:Provider",
    }
