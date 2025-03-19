# ruff: noqa: I001, F401
# mypy: ignore-errors

# Level two import sibling
from .emod_c import square as esquare


def square(x):
    return x * x
