"""
Make documentation for the skbuild model in sphinx format.
"""

from __future__ import annotations

import dataclasses
import textwrap
import typing
from collections import OrderedDict

from .._compat.typing import Annotated, get_args, get_origin
from .documentation import mk_docs
from .skbuild_model import ScikitBuildSettings

if typing.TYPE_CHECKING:
    from .documentation import DCDoc

__all__ = ["mk_skbuild_docs"]


def __dir__() -> list[str]:
    return __all__


def _env_expressible(field_type: typing.Any) -> bool:
    """
    Whether a field can be set through a flat ``SKBUILD_*`` environment variable.

    Nested mappings (e.g. a dict of dicts) can't round-trip through a single
    environment string, so no env var is advertised for them. Dicts of scalars
    (including ``cmake.define``) and lists of scalars are fine.
    """
    origin = get_origin(field_type)
    if origin is Annotated:
        return _env_expressible(get_args(field_type)[0])
    if origin is typing.Union:
        return all(
            _env_expressible(arg)
            for arg in get_args(field_type)
            if arg is not type(None)
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
      :type: ``{item.type}``{sphinx_default}{sphinx_env}

      {docs}
    ```
    """)
    item: DCDoc

    def ignore_default(self) -> bool:
        """
        Check if we want to ignore displaying the default
        """
        return self.item.default in ('""', "[]", "{}")

    def default(self) -> str:
        """
        Formatted text that includes the `:default:` key or not
        """
        if self.ignore_default():
            return ""
        return f"\n  :default: {self.item.default}"

    def env(self) -> str:
        """
        Formatted text with the equivalent ``SKBUILD_*`` environment variable.

        Arrays of tables (``generate[]``) and nested mappings can't be expressed
        as environment variables, so they are skipped.
        """
        if "[]" in self.item.name or not _env_expressible(self.item.field.type):
            return ""
        var = self.item.name.replace(".", "_").replace("-", "_").upper()
        return f"\n  :env: ``SKBUILD_{var}``"

    def format(self) -> str:
        # Replace all new-lines with appropriately rst indented lines
        docs = self.item.docs.replace("\n", "\n  ")
        # Replace all lines with pure whitespace to satisfy pre-commit
        docs = docs.replace("\n  \n", "\n\n")
        return self.TEMPLATE.format(
            item=self.item,
            sphinx_default=self.default(),
            sphinx_env=self.env(),
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
