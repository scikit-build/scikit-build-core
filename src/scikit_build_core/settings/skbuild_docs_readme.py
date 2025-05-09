from __future__ import annotations

import dataclasses
import textwrap
import typing

from .documentation import mk_docs
from .skbuild_model import ScikitBuildSettings

if typing.TYPE_CHECKING:
    from .documentation import DCDoc

__all__ = ["mk_skbuild_docs"]


def __dir__() -> list[str]:
    return __all__


@dataclasses.dataclass
class Document:
    items: list[Item]

    def format(self) -> str:
        return "\n".join(item.format() for item in self.items)


@dataclasses.dataclass
class Item:
    TEMPLATE: typing.ClassVar[str] = textwrap.dedent("""\
    {summary}
    {item.name} = {item.default}
    """)
    item: DCDoc

    def format(self) -> str:
        summary = self.item.docs.split("\n", maxsplit=1)[0]
        return self.TEMPLATE.format(
            item=self.item,
            summary=f"# {summary}",
        )


def mk_skbuild_docs() -> str:
    """
    Makes documentation for the skbuild model.
    """
    doc = Document(
        [Item(item) for item in mk_docs(ScikitBuildSettings) if not item.deprecated]
    )
    return doc.format()


if __name__ == "__main__":
    print(mk_skbuild_docs())  # noqa: T201
