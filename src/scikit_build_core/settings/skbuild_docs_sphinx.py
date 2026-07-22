"""
Make documentation for the skbuild model in sphinx format.
"""

from __future__ import annotations

__lazy_modules__ = {
    "collections",
    f"{__spec__.parent}.skbuild_model",
    "textwrap",
    "typing",
}

import dataclasses
import textwrap
import typing
from collections import OrderedDict
from typing import Annotated, get_args, get_origin

from .documentation import mk_docs
from .skbuild_model import ScikitBuildSettings

TYPE_CHECKING = False

if TYPE_CHECKING:
    from .documentation import DCDoc

__all__ = ["mk_skbuild_docs"]

_NONE_TYPE = type(None)


def __dir__() -> list[str]:
    return __all__


def _flat_expressible(field_type: typing.Any) -> bool:
    """
    Whether a field can be set through a flat source (``config-settings`` or a
    ``SKBUILD_*`` environment variable).

    Both sources reject arrays of tables (handled separately via the ``[]`` name
    marker) and can't round-trip nested mappings (e.g. a dict of dicts), so no
    flat key is advertised for those. Dicts of scalars (including
    ``cmake.define``) and lists of scalars are fine.
    """
    origin = get_origin(field_type)
    if origin is Annotated:
        return _flat_expressible(get_args(field_type)[0])
    if origin is typing.Union:
        return all(
            _flat_expressible(arg)
            for arg in get_args(field_type)
            if arg is not _NONE_TYPE
        )
    if origin is dict:
        return get_origin(get_args(field_type)[1]) not in (dict, list)
    return True


@dataclasses.dataclass
class Document:
    sections: dict[str, Section] = dataclasses.field(
        default_factory=OrderedDict, init=False
    )

    def format(self) -> str:
        return "\n".join(self.sections[it].format() for it in sorted(self.sections))


@dataclasses.dataclass
class Section:
    TEMPLATE: typing.ClassVar[str] = textwrap.dedent("""\
    {section_level} {section}

    {content}""")
    name: str
    level: int = 2
    items: dict[str, Item] = dataclasses.field(default_factory=OrderedDict, init=False)

    def format(self) -> str:
        return self.TEMPLATE.format(
            section=self.name,
            section_level="#" * self.level,
            content="\n".join(self.items[it].format() for it in sorted(self.items)),
        )


@dataclasses.dataclass
class Item:
    TEMPLATE: typing.ClassVar[str] = textwrap.dedent("""\
    ```{{eval-rst}}
    .. confval:: {item.name}

    {fields}

      {docs}
    ```
    """)
    item: DCDoc

    def ignore_default(self) -> bool:
        """
        Check if we want to ignore displaying the default
        """
        return self.item.default in ('""', "[]", "{}")

    def flat_expressible(self) -> bool:
        """
        Whether the option can be set via ``config-settings`` or an env var.

        Arrays of tables (``generate[]``) and nested mappings can only be set in
        ``pyproject.toml``, so the flat forms are skipped for them.
        """
        return "[]" not in self.item.name and _flat_expressible(self.item.field.type)

    def fields(self) -> str:
        """
        The rST field list rendered inside the confval body.

        Besides type and default, this advertises the equivalent
        ``config-settings`` keys (bare and ``skbuild.``-prefixed) and the
        ``SKBUILD_*`` environment variable, where those forms apply.
        """
        lines = [f":Type: ``{self.item.type}``"]
        if not self.ignore_default():
            lines.append(f":Default: {self.item.default}")
        if self.flat_expressible():
            name = self.item.name
            var = name.replace(".", "_").replace("-", "_").upper()
            lines.append(f":Config-settings: ``{name}`` or ``skbuild.{name}``")
            lines.append(f":Environment variable: ``SKBUILD_{var}``")
        return "\n".join(f"  {line}" for line in lines)

    def format(self) -> str:
        # Replace all new-lines with appropriately rst indented lines
        docs = self.item.docs.replace("\n", "\n  ")
        # Replace all lines with pure whitespace to satisfy pre-commit
        docs = docs.replace("\n  \n", "\n\n")
        return self.TEMPLATE.format(
            item=self.item,
            fields=self.fields(),
            docs=docs,
        )


def mk_skbuild_docs() -> str:
    doc = Document()
    for doc_item in mk_docs(ScikitBuildSettings):
        name_split = doc_item.name.rsplit(".", maxsplit=1)
        section_name = f"{name_split[0]}" if len(name_split) > 1 else "(top-level)"
        section = doc.sections.setdefault(section_name, Section(section_name))
        section.items[doc_item.name] = Item(doc_item)
    return doc.format()


if __name__ == "__main__":
    print(mk_skbuild_docs())  # noqa: T201
