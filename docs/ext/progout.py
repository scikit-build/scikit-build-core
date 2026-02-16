from __future__ import annotations

import os
import re
import subprocess
from pathlib import Path
from typing import TYPE_CHECKING, Any, ClassVar

from docutils import nodes
from docutils.parsers.rst import Directive

if TYPE_CHECKING:
    from collections.abc import Generator


ROOT = Path(__file__).parent.parent.parent.resolve()


ANSI_ESCAPE = re.compile(r"\x1b\[([0-9;]*)m")

ANSI_COLORS = {
    "30": "#000000",  # black
    "31": "#dc3545",  # red
    "32": "#28a745",  # green
    "33": "#ffc107",  # yellow
    "34": "#007bff",  # blue
    "35": "#6f42c1",  # magenta
    "36": "#17a2b8",  # cyan
    "37": "#f8f9fa",  # white
    "90": "#6c757d",  # bright black (gray)
    "91": "#ff6b6b",  # bright red
    "92": "#51cf66",  # bright green
    "93": "#ffd43b",  # bright yellow
    "94": "#4d7fff",  # bright blue
    "95": "#da77f2",  # bright magenta
    "96": "#15aabf",  # bright cyan
    "97": "#ffffff",  # bright white
}


class AnsiToHtmlConverter:
    """Convert ANSI escape codes to HTML with state tracking."""

    def __init__(self) -> None:
        self.open_spans = 0

    def process_codes(self, codes_str: str) -> Generator[str, None, None]:
        """Process ANSI codes and yield corresponding HTML."""
        codes = codes_str.split(";") if codes_str else ["0"]

        for code in codes:
            if code == "0":
                # Reset - close all open spans
                if self.open_spans > 0:
                    yield "</span>" * self.open_spans
                    self.open_spans = 0
            elif code == "1":
                # Bold
                yield '<span style="font-weight: bold;">'
                self.open_spans += 1
            elif code in ANSI_COLORS:
                # Foreground color
                color = ANSI_COLORS[code]
                yield f'<span style="color: {color};">'
                self.open_spans += 1

    def convert(self, text: str) -> str:
        """Convert ANSI escape codes in text to HTML spans."""
        last_end = 0
        result: list[str] = []
        for match in ANSI_ESCAPE.finditer(text):
            # Add text before the match
            result.append(text[last_end : match.start()])
            # Process the ANSI code
            result.extend(self.process_codes(match.group(1)))
            last_end = match.end()

        # Add remaining text
        result.append(text[last_end:])

        # Close any remaining open spans at the end
        if self.open_spans > 0:
            result.append("</span>" * self.open_spans)
            self.open_spans = 0

        return "".join(result)


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

        try:
            # Run the command and capture output
            result = subprocess.run(
                command.split(),
                capture_output=True,
                check=True,
                text=True,
                cwd=str(cwd),
                env={**os.environ, "FORCE_COLOR": "1"},
            )
            output = result.stdout or result.stderr
        except Exception as e:  # noqa: BLE001
            return [
                nodes.error(
                    None,
                    nodes.paragraph(text=f"Error running command: {command}\n{e}"),
                )
            ]

        # Convert ANSI codes to HTML
        html_output = AnsiToHtmlConverter().convert(output)

        # Add the run block if this was `command-output`
        if self.name == "command-output":
            color = ANSI_COLORS["90"]
            html_output = f'<span style="color: {color};">$</span> <span style="font-weight: bold;">{command}</span>\n{html_output}'

        # Create a raw HTML node with the colored output
        raw_html = nodes.raw("", html_output, format="html")
        literal_block = nodes.literal_block(output, raw_html)
        literal_block["language"] = "text"

        # Return as a container with pre styling
        container = nodes.container()
        container += nodes.raw(
            "",
            f'<div class="highlight-text notranslate"><div class="highlight"><pre>{html_output}</pre></div></div>',
            format="html",
        )
        return [container]


def setup(app: Any) -> dict[str, Any]:
    app.add_directive("program-output", ShowCliDirective)
    app.add_directive("command-output", ShowCliDirective)

    return {
        "version": "0.1",
        "parallel_read_safe": True,
        "parallel_write_safe": True,
    }
