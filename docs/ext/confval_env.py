"""Extend the std-domain ``confval`` directive with extra naming options.

Sphinx's built-in ``confval`` directive only renders ``:type:`` and
``:default:`` fields. scikit-build-core options can also be set through PEP 517
``config-settings`` and ``SKBUILD_*`` environment variables, so this override
adds ``:config-settings:`` and ``:env:`` options rendered in the same field
list, right after ``:default:``.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, ClassVar

from docutils import nodes
from docutils.parsers.rst import directives
from sphinx.domains.std import ConfigurationValue
from sphinx.locale import _

if TYPE_CHECKING:
    from sphinx.application import Sphinx
    from sphinx.util.typing import OptionSpec

# Extra ``:option:`` keys, in render order, mapped to their field labels.
_EXTRA_FIELDS = (
    ("config-settings", _("config-settings")),
    ("env", _("Environment variable")),
)


class EnvConfigurationValue(ConfigurationValue):
    option_spec: ClassVar[OptionSpec] = {
        **ConfigurationValue.option_spec,
        "config-settings": directives.unchanged_required,
        "env": directives.unchanged_required,
    }

    def transform_content(self, content_node: nodes.Element) -> None:
        # Let the base class build the Type/Default field list first.
        super().transform_content(content_node)

        if content_node.children and isinstance(content_node[0], nodes.field_list):
            field_list = content_node[0]
        else:
            field_list = nodes.field_list()
            content_node.insert(0, field_list)

        for key, label in _EXTRA_FIELDS:
            if key not in self.options:
                continue
            parsed, msgs = self.parse_inline(self.options[key], lineno=self.lineno)
            field_list.append(
                nodes.field(
                    "",
                    nodes.field_name("", label),
                    nodes.field_body("", *parsed),
                )
            )
            field_list += msgs


def setup(app: Sphinx) -> dict[str, object]:
    app.add_directive_to_domain("std", "confval", EnvConfigurationValue, override=True)

    return {
        "version": "0.1",
        "parallel_read_safe": True,
        "parallel_write_safe": True,
    }
