# ruff: noqa: I001, F401
# mypy: ignore-errors

# Level one import sibling
from .emod_a import square as esquare


def square(x):
    return x * x
