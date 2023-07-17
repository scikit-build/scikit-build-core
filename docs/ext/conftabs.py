from __future__ import annotations

import textwrap

from docutils import nodes
from docutils.statemachine import StringList
from sphinx.util.docutils import SphinxDirective


class ConfTabs(SphinxDirective):
    required_arguments = 2
    final_argument_whitespace = True

    def run(self):
        name, result = self.arguments
        env_name = f"SKBUILD_{name.replace('.', '_').upper()}"
        value_result = eval(result, {}, {})  # noqa: PGH001
        if isinstance(value_result, list):
            joined_result = ";".join(value_result)
        elif isinstance(value_result, bool):
            result = joined_result = "true" if value_result else "false"
        else:
            joined_result = result

        pyproject = textwrap.dedent(
            f"""\
        ````{{tab}} pyproject.toml

        ```toml
        [tool.scikit-build]
        {name} = {result}
        ```

        ````

        `````{{tab}} config-settings


        ````{{tab}} pip

        ```console
        $ pip install . --config-settings={name}={joined_result}
        ```

        ````

        ````{{tab}} build

        ```console
        $ pipx run build --wheel -C{name}={joined_result}
        ```

        ````

        ````{{tab}} cibuildwheel

        ```toml
        [tool.cibuildwheel.config-settings]
        "{name}" = {result}
        ```

        ````

        `````

        ````{{tab}} Environment

        ```yaml
        {env_name}: {joined_result}
        ```

        ````
        """
        )

        content = nodes.container("")
        self.state.nested_parse(
            StringList(pyproject.splitlines()), self.content_offset, content
        )

        return [content]


def setup(app):
    app.add_directive("conftabs", ConfTabs)

    return {
        "version": "0.1",
        "parallel_read_safe": True,
        "parallel_write_safe": True,
    }
