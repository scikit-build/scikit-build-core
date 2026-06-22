"""Extend the std-domain ``confval`` directive with an ``:env:`` option.

Sphinx's built-in ``confval`` directive only renders ``:type:`` and
``:default:`` fields. scikit-build-core options can also be set via an
environment variable, so this override adds an ``:env:`` option that is
rendered in the same field list, right after ``:default:``.
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


class EnvConfigurationValue(ConfigurationValue):
    option_spec: ClassVar[OptionSpec] = {
        **ConfigurationValue.option_spec,
        "env": directives.unchanged_required,
    }

    def transform_content(self, content_node: nodes.Element) -> None:
        # Let the base class build the Type/Default field list first.
        super().transform_content(content_node)
        if "env" not in self.options:
            return

        parsed, msgs = self.parse_inline(self.options["env"], lineno=self.lineno)
        field = nodes.field(
            "",
            nodes.field_name("", _("Environment variable")),
            nodes.field_body("", *parsed),
        )
        # The base class inserts a field list at position 0 when type/default
        # are present; append to it so every key renders together.
        if content_node.children and isinstance(content_node[0], nodes.field_list):
            content_node[0].append(field)
            content_node[0] += msgs
        else:
            content_node.insert(0, nodes.field_list("", field, *msgs))


def setup(app: Sphinx) -> dict[str, object]:
    app.add_directive_to_domain("std", "confval", EnvConfigurationValue, override=True)

    return {
        "version": "0.1",
        "parallel_read_safe": True,
        "parallel_write_safe": True,
    }
