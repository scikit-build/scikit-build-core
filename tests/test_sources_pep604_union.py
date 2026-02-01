# mypy: ignore-errors
import sys
from typing import Union, get_origin

import pytest

# Skip entire module on Python < 3.10
pytestmark = pytest.mark.skipif(
    sys.version_info < (3, 10), reason="PEP 604 union syntax requires Python 3.10+"
)


def test_pep604_union_recognized():
    """Ensure PEP 604 unions (A | B) are handled like typing.Union."""
    import types

    from scikit_build_core.settings.sources import _is_union_type

    # PEP 604 syntax - only valid at runtime on 3.10+
    pep604_union = list[str] | str
    assert get_origin(pep604_union) is types.UnionType
    assert _is_union_type(types.UnionType)

    # typing.Union syntax (works on all versions)
    typing_union = Union[list[str], str]
    assert get_origin(typing_union) is Union
    assert _is_union_type(Union)


def test_process_union_pep604():
    """Test _process_union handles PEP 604 unions."""
    from scikit_build_core.settings.sources import _process_union

    pep604_union = list[str] | str
    result = _process_union(pep604_union)
    assert result is not None
