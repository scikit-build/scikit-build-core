# ruff: noqa: F401
# mypy: ignore-errors

# Level three import sibling
from .emod_e import square as esquare


def square(x):
    return x * x
