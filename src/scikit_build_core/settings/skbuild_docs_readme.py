from __future__ import annotations

__lazy_modules__ = {f"{__spec__.parent}.skbuild_model", "typing"}

import dataclasses
import typing

from .documentation import mk_docs
from .skbuild_model import ScikitBuildSettings

TYPE_CHECKING = False

if TYPE_CHECKING:
    from .documentation import DCDoc

__all__ = ["mk_skbuild_docs"]


def __dir__() -> list[str]:
    return __all__


@dataclasses.dataclass
class Document:
    sections: list[Section]

    def format(self) -> str:
        return "\n\n".join(section.format() for section in self.sections)


@dataclasses.dataclass
class Section:
    HEADER: typing.ClassVar[str] = "| Option | Default | Description |\n| - | - | - |"
    name: str | None
    items: list[Item]

    def format(self) -> str:
        title = "Top-level" if self.name is None else f"`{self.name}`"
        return "\n".join(
            [f"### {title}", "", self.HEADER, *(i.format() for i in self.items)]
        )


@dataclasses.dataclass
class Item:
    item: DCDoc

    def format(self) -> str:
        summary = self.item.docs.split("\n", maxsplit=1)[0].replace("|", "\\|")
        value, _, comment = self.item.default.partition("  # ")
        default = f"`{value}`" + (f" ({comment})" if comment else "")
        return f"| `{self.item.name}` | {default} | {summary} |"


def mk_skbuild_docs() -> str:
    """
    Makes documentation for the skbuild model.
    """
    sections: dict[str | None, list[Item]] = {}
    for item in mk_docs(ScikitBuildSettings):
        if item.deprecated or item.override_only:
            continue
        prefix, sep, _ = item.name.partition(".")
        sections.setdefault(prefix if sep else None, []).append(Item(item))

    ordered = [None, *(name for name in sections if name is not None)]
    doc = Document(
        [Section(name, sections[name]) for name in ordered if name in sections]
    )
    return doc.format()


if __name__ == "__main__":
    print(mk_skbuild_docs())  # noqa: T201
