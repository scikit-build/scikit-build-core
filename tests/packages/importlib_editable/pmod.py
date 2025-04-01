# ruff: noqa: I001, F401
# mypy: ignore-errors

# Level zero import global sibling
from emod import square as esquare


def square(x):
    return x * x
