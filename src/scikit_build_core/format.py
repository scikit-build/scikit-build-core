"""Format variables available in the ``pyproject.toml`` evaluation"""

from __future__ import annotations

from typing import TYPE_CHECKING, TypedDict

if TYPE_CHECKING:
    from scikit_build_core.settings.skbuild_model import ScikitBuildSettings

__all__ = [
    "PyprojectFormatter",
    "pyproject_format",
]


def __dir__() -> list[str]:
    return __all__


class PyprojectFormatter(TypedDict, total=False):
    """Format helper for pyproject.toml.

    Stores all known variables that can be used for evaluating a formatted string
    in the pyproject.toml config file.
    """


def pyproject_format(
    *,
    settings: ScikitBuildSettings | None = None,  # noqa: ARG001
    dummy: bool = False,
) -> PyprojectFormatter | dict[str, str]:
    """Generate :py:class:`PyprojectFormatter` dictionary to use in f-string format."""
    if dummy:
        # Return a dict with all the known keys but with values replaced with dummy values
        return {key: "*" for key in PyprojectFormatter.__annotations__}
    return PyprojectFormatter()
