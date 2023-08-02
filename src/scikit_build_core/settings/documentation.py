from __future__ import annotations

import ast
import inspect
import sys
import textwrap

__all__ = ["pull_docs"]


def __dir__() -> list[str]:
    return __all__


def _get_value(value: ast.expr) -> str:
    if sys.version_info < (3, 8):
        assert isinstance(value, ast.Str)
        return value.s

    assert isinstance(value, ast.Constant)
    return value.value


def pull_docs(dc: type[object]) -> dict[str, str]:
    """
    Pulls documentation from a dataclass.
    """
    t = ast.parse(inspect.getsource(dc))
    (obody,) = t.body
    assert isinstance(obody, ast.ClassDef)
    body = obody.body
    return {
        assign.target.id: textwrap.dedent(_get_value(expr.value)).strip().replace("\n", " ")  # type: ignore[union-attr]
        for assign, expr in zip(body[:-1], body[1:])
        if isinstance(assign, ast.AnnAssign) and isinstance(expr, ast.Expr)
    }
