from __future__ import annotations

from typing import Annotated, Dict, List, Optional, Union

import pytest

from scikit_build_core.utils.typing import (
    get_inner_type,
    get_target_raw_type,
    is_union_type,
    process_annotated,
    process_union,
)


def test_process_union_basic():
    assert process_union(Union[str, int]) == Union[str, int]


def test_process_union_with_none():
    assert process_union(Optional[str]) is str


def test_process_union_only_none():
    assert process_union(type(None)) is type(None)


def test_process_annotated_basic():
    assert process_annotated(Annotated[str, "meta"]) == (str, ("meta",))  # type: ignore[arg-type]


def test_process_annotated_not_annotated():
    assert process_annotated(str) == (str, ())


def test_get_target_raw_type_optional():
    assert get_target_raw_type(Optional[str]) is str


def test_get_target_raw_type_dict():
    assert get_target_raw_type(Dict[str, int]) is dict


def test_is_union_type():
    assert is_union_type(Union) is True


def test_get_inner_type_list():
    assert get_inner_type(List[str]) is str


def test_get_inner_type_dict():
    assert get_inner_type(Dict[str, int]) is int


def test_get_inner_type_invalid():
    with pytest.raises(AssertionError, match="Expected a list or dict"):
        get_inner_type(str)
