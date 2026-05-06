from __future__ import annotations

import pytest

from scikit_build_core.metadata.regex import dynamic_metadata as regex_metadata
from scikit_build_core.metadata.template import dynamic_metadata as template_metadata

# ---- template tests ----


def test_template_missing_result():
    with pytest.raises(RuntimeError, match="Must contain the 'result'"):
        template_metadata("version", {}, {})


def test_template_extra_keys():
    with pytest.raises(RuntimeError, match=r"Only .* settings allowed"):
        template_metadata("version", {"result": "{version}", "extra": "nope"}, {})


def test_template_basic():
    result = template_metadata(
        "version", {"result": "v={project[version]}"}, project={"version": "1.0"}
    )
    assert result == "v=1.0"


# ---- regex tests ----


def test_regex_missing_input():
    with pytest.raises(RuntimeError, match="Must contain the 'input' setting"):
        regex_metadata("version", {"regex": r"v=(.*)"})


def test_regex_extra_keys():
    with pytest.raises(RuntimeError, match=r"Only .* settings allowed"):
        regex_metadata(
            "version",
            {
                "input": "x",
                "regex": r"v=(.*)",
                "result": "{1}",
                "remove": "",
                "extra": "nope",
            },
        )


def test_regex_non_string_setting():
    with pytest.raises(RuntimeError, match="Setting 'input' must be a string"):
        regex_metadata("version", {"input": 123})


def test_regex_missing_regex_for_non_version():
    with pytest.raises(RuntimeError, match="Must contain the 'regex' setting"):
        regex_metadata("readme", {"input": "version.py"})


def test_regex_no_match(tmp_path):
    f = tmp_path / "version.py"
    f.write_text("no version here")
    with pytest.raises(RuntimeError, match="Couldn't find"):
        regex_metadata("version", {"input": str(f)})


def test_regex_default_version_pattern(tmp_path):
    f = tmp_path / "version.py"
    f.write_text('__version__ = "1.2.3"')
    result = regex_metadata("version", {"input": str(f)})
    assert result == "1.2.3"


def test_regex_custom_pattern(tmp_path):
    f = tmp_path / "version.py"
    f.write_text("release: v=1.0.0")
    result = regex_metadata(
        "version", {"input": str(f), "regex": r"v=(?P<val>.*)", "result": "{val}"}
    )
    assert result == "1.0.0"


def test_regex_remove(tmp_path):
    f = tmp_path / "version.py"
    f.write_text('__version__ = "1.2.3-alpha"')
    result = regex_metadata("version", {"input": str(f), "remove": r"-alpha"})
    assert result == "1.2.3"


# ---- setuptools_scm tests ----


def test_setuptools_scm_only_version():
    from scikit_build_core.metadata.setuptools_scm import dynamic_metadata

    with pytest.raises(ValueError, match="Only the 'version' field"):
        dynamic_metadata("readme")


def test_setuptools_scm_no_settings():
    from scikit_build_core.metadata.setuptools_scm import dynamic_metadata

    with pytest.raises(ValueError, match="No inline configuration"):
        dynamic_metadata("version", {"something": "else"})


def test_setuptools_scm_get_requires():
    from scikit_build_core.metadata.setuptools_scm import (
        get_requires_for_dynamic_metadata,
    )

    assert get_requires_for_dynamic_metadata() == ["setuptools-scm"]


# ---- fancy_pypi_readme tests ----


def test_fancy_pypi_readme_only_readme():
    from scikit_build_core.metadata.fancy_pypi_readme import dynamic_metadata

    with pytest.raises(ValueError, match="Only the 'readme' field"):
        dynamic_metadata("version", {}, {})


def test_fancy_pypi_readme_no_settings():
    from scikit_build_core.metadata.fancy_pypi_readme import dynamic_metadata

    with pytest.raises(ValueError, match="No inline configuration"):
        dynamic_metadata("readme", {"something": "else"}, {})


def test_fancy_pypi_readme_get_requires():
    from scikit_build_core.metadata.fancy_pypi_readme import (
        get_requires_for_dynamic_metadata,
    )

    assert get_requires_for_dynamic_metadata() == ["hatch-fancy-pypi-readme>=23.2"]
