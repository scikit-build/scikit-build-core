from pathlib import Path
from typing import Any, Dict, List, Optional, Union

import pytest
from packaging.version import Version

from scikit_build_core.settings.json_schema import FailedConversion, convert_type


def test_convert_str():
    assert convert_type(str) == {"type": "string"}


def test_convert_str_or_bool():
    assert convert_type(Union[str, bool]) == {
        "oneOf": [{"type": "string"}, {"type": "boolean"}]
    }


def test_convert_optional_str():
    assert convert_type(Optional[str]) == {"type": "string"}


def test_convert_path():
    assert convert_type(Path) == {"type": "string"}


def test_convert_version():
    assert convert_type(Version) == {"type": "string"}


def test_convert_list():
    assert convert_type(List[str]) == {"type": "array", "items": {"type": "string"}}
    assert convert_type(List[Union[str, bool]]) == {
        "type": "array",
        "items": {"oneOf": [{"type": "string"}, {"type": "boolean"}]},
    }


def test_convert_dict():
    assert convert_type(Dict[str, str]) == {
        "type": "object",
        "patternProperties": {".+": {"type": "string"}},
    }
    assert convert_type(Dict[str, Dict[str, str]]) == {
        "type": "object",
        "patternProperties": {
            ".+": {"type": "object", "patternProperties": {".+": {"type": "string"}}}
        },
    }
    assert convert_type(Dict[str, Any]) == {
        "type": "object",
    }


def test_convert_invalid():
    with pytest.raises(FailedConversion):
        convert_type(object)
