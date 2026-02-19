from __future__ import annotations

import os
import re
import shlex
import subprocess
from pathlib import Path
from typing import Any, ClassVar

from docutils import nodes
from docutils.parsers.rst import Directive, directives


class ShowCliDirective(Directive):
    """Include the output of a CLI command in the documentation."""

    has_content = False
    required_arguments = 1
    optional_arguments = 0
    final_argument_whitespace = True
    option_spec: ClassVar = {"cwd": str}

    def run(self) -> list[Any]:
        """Execute the command and return its output as a code block."""
        command = self.arguments[0]

        # Get the directory of the current file being processed
        source_file = Path(self.state.document.current_source)
        current_dir = source_file.parent

        # Get the cwd option, defaulting to the current file's directory
        cwd_option = self.options.get("cwd")
        cwd = (current_dir / cwd_option).resolve() if cwd_option else current_dir
        env = os.environ
        env["FORCE_COLOR"] = "1"
        env.pop("NO_COLOR", None)

        try:
            # Run the command and capture output
            result = subprocess.run(
                shlex.split(command),
                capture_output=True,
                check=True,
                text=True,
                cwd=str(cwd),
                env=env,
            )
            output = result.stdout or result.stderr
        except subprocess.CalledProcessError as e:
            return [
                nodes.error(
                    None,
                    nodes.paragraph(text=f"Error running command: {command}\n{e}"),
                )
            ]

        # Add the run block if this was `command-output`
        if self.name == "command-output":
            output = f"\x1b[90m$\x1b[0m \x1b[1m{command}\x1b[0m\n{output}"

        # Try to use the erbsland-ansi directive if available
        ansi_directive_class, _ = directives.directive(
            "erbsland-ansi", self.state.memo.language, self.state.document
        )

        if ansi_directive_class is not None:
            ansi_directive = ansi_directive_class(
                name="erbsland-ansi",
                arguments=[],
                options={},
                content=output.splitlines(),
                lineno=self.lineno,
                content_offset=0,
                block_text="",
                state=self.state,
                state_machine=self.state_machine,
            )

            return ansi_directive.run()

        # Fall back to plain text with ANSI codes stripped
        ansi_escape = re.compile(r"\x1b\[[0-9;]*m")
        plain_output = ansi_escape.sub("", output)

        literal = nodes.literal_block(plain_output, plain_output)
        literal["language"] = "text"
        return [literal]


def setup(app: Any) -> dict[str, Any]:
    app.add_directive("program-output", ShowCliDirective)
    app.add_directive("command-output", ShowCliDirective)

    return {
        "version": "0.1",
        "parallel_read_safe": True,
        "parallel_write_safe": True,
    }
