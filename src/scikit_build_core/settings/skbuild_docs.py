from __future__ import annotations

from .documentation import mk_docs
from .skbuild_model import ScikitBuildSettings

__all__ = ["mk_skbuild_docs"]


def __dir__() -> list[str]:
    return __all__


def mk_skbuild_docs() -> str:
    """
    Makes documentation for the skbuild model.
    """
    return "\n".join(
        str(item) for item in mk_docs(ScikitBuildSettings) if not item.deprecated
    )


if __name__ == "__main__":
    print(mk_skbuild_docs())  # noqa: T201
